"""
文档管理视图
"""
import logging
import os
import uuid
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q

from apps.knowledge_base.models import KnowledgeBase
from .models import Document, Paragraph, Problem, ProblemParagraphMapping, DocumentType, DocumentStatus
from .serializers import (
    DocumentListSerializer, DocumentDetailSerializer, DocumentCreateSerializer,
    DocumentUpdateSerializer, DocumentUploadSerializer, DocumentBatchSerializer,
    WebDocumentSerializer, QADocumentSerializer, DocumentSearchSerializer,
    DocumentStatsSerializer, ParagraphSerializer, ProblemSerializer,
    DocumentProcessingTaskSerializer
)
from .services import DocumentProcessingService, WebScrapingService, EmbeddingService

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    文档管理视图集
    """
    serializer_class = DocumentListSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        """获取查询集"""
        knowledge_base_id = self.kwargs.get('knowledge_base_id')
        knowledge_base = get_object_or_404(
            KnowledgeBase,
            id=knowledge_base_id,
            created_by=self.request.user
        )
        return Document.objects.filter(
            knowledge_base=knowledge_base,
            is_deleted=False
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        """根据action选择序列化器"""
        if self.action == 'list':
            return DocumentListSerializer
        elif self.action == 'retrieve':
            return DocumentDetailSerializer
        elif self.action == 'create':
            return DocumentCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return DocumentUpdateSerializer
        elif self.action == 'upload':
            return DocumentUploadSerializer
        elif self.action == 'batch_operation':
            return DocumentBatchSerializer
        elif self.action == 'create_web':
            return WebDocumentSerializer
        elif self.action == 'create_qa':
            return QADocumentSerializer
        elif self.action == 'search':
            return DocumentSearchSerializer
        elif self.action == 'stats':
            return DocumentStatsSerializer
        return DocumentListSerializer
    
    def get_knowledge_base(self):
        """获取知识库"""
        knowledge_base_id = self.kwargs.get('knowledge_base_id')
        return get_object_or_404(
            KnowledgeBase,
            id=knowledge_base_id,
            created_by=self.request.user
        )
    
    def get_serializer_context(self):
        """获取序列化器上下文"""
        context = super().get_serializer_context()
        context['knowledge_base'] = self.get_knowledge_base()
        return context
    
    def list(self, request, *args, **kwargs):
        """获取文档列表"""
        queryset = self.get_queryset()
        
        # 过滤条件
        document_type = request.query_params.get('type')
        document_status = request.query_params.get('status')
        search = request.query_params.get('search')
        
        if document_type:
            queryset = queryset.filter(type=document_type)
        if document_status:
            queryset = queryset.filter(status=document_status)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(paragraphs__content__icontains=search)
            ).distinct()
        
        # 分页
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """创建文档"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        document = serializer.save()
        
        # 异步处理文档
        DocumentProcessingService.process_document_async(document)
        
        return Response(
            DocumentDetailSerializer(document).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def upload(self, request, *args, **kwargs):
        """上传文档"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        file = serializer.validated_data['file']
        name = serializer.validated_data.get('name', file.name)
        doc_type = serializer.validated_data.get('type', 'base')
        
        knowledge_base = self.get_knowledge_base()
        
        # 保存文件
        file_path = f"documents/{knowledge_base.id}/{uuid.uuid4()}_{file.name}"
        saved_path = default_storage.save(file_path, file)
        
        # 创建文档记录
        document = Document.objects.create(
            knowledge_base=knowledge_base,
            created_by=request.user,
            name=name,
            type=doc_type,
            file_path=saved_path,
            file_size=file.size,
            hit_handling_method=serializer.validated_data['hit_handling_method'],
            directly_return_similarity=serializer.validated_data['directly_return_similarity'],
            status=DocumentStatus.PROCESSING
        )
        
        # 异步处理文档
        DocumentProcessingService.process_document_async(document)
        
        return Response(
            DocumentDetailSerializer(document).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def create_web(self, request, *args, **kwargs):
        """创建Web文档"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        url = serializer.validated_data['url']
        name = serializer.validated_data.get('name', url)
        selector = serializer.validated_data.get('selector', '')
        depth = serializer.validated_data.get('depth', 1)
        
        knowledge_base = self.get_knowledge_base()
        
        # 创建文档记录
        document = Document.objects.create(
            knowledge_base=knowledge_base,
            created_by=request.user,
            name=name,
            type=DocumentType.WEB,
            status=DocumentStatus.PROCESSING,
            meta={
                'source_url': url,
                'selector': selector,
                'depth': depth
            }
        )
        
        # 异步抓取网页内容
        WebScrapingService.scrape_web_async(document, url, selector, depth)
        
        return Response(
            DocumentDetailSerializer(document).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'])
    def create_qa(self, request, *args, **kwargs):
        """Create a QA document and trigger background embeddings for its answers."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qa_pairs = serializer.validated_data['qa_pairs']
        name = serializer.validated_data.get('name', f'QA-{timezone.now().strftime("%Y%m%d%H%M%S")}')
        knowledge_base = self.get_knowledge_base()

        with transaction.atomic():
            document = Document.objects.create(
                knowledge_base=knowledge_base,
                created_by=request.user,
                name=name,
                type=DocumentType.QA,
                status=DocumentStatus.EMBEDDING,
            )

            for i, qa_pair in enumerate(qa_pairs):
                problem = Problem.objects.create(
                    knowledge_base=knowledge_base,
                    content=qa_pair['question'],
                )
                paragraph = Paragraph.objects.create(
                    document=document,
                    knowledge_base=knowledge_base,
                    title=qa_pair['question'],
                    content=qa_pair['answer'],
                    position=i,
                    status=DocumentStatus.PENDING,
                )
                ProblemParagraphMapping.objects.create(
                    knowledge_base=knowledge_base,
                    document=document,
                    problem=problem,
                    paragraph=paragraph,
                )

            document.update_stats()
            document.save(update_fields=['status', 'paragraph_count', 'char_length', 'updated_at'])

        logger.info(
            'document_qa_create_request user_id=%s knowledge_base_id=%s document_id=%s qa_pair_count=%s',
            request.user.id,
            knowledge_base.id,
            document.id,
            len(qa_pairs),
        )
        EmbeddingService.embed_paragraphs_async(document)

        return Response(
            DocumentDetailSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def reprocess(self, request, *args, **kwargs):
        """重新处理文档"""
        document = self.get_object()
        
        # 重置状态
        document.status = DocumentStatus.PROCESSING
        document.save()
        
        # 清理旧数据
        document.paragraphs.all().delete()
        
        # 重新处理
        DocumentProcessingService.process_document_async(document)
        
        return Response({'message': '文档重新处理已开始'})
    
    @action(detail=False, methods=['post'])
    def batch_operation(self, request, *args, **kwargs):
        """批量操作文档"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        document_ids = serializer.validated_data['document_ids']
        action_type = serializer.validated_data['action']
        
        knowledge_base = self.get_knowledge_base()
        documents = Document.objects.filter(
            knowledge_base=knowledge_base,
            id__in=document_ids,
            is_deleted=False
        )
        
        if action_type == 'delete':
            documents.update(is_deleted=True, deleted_at=timezone.now())
            message = f'成功删除 {documents.count()} 个文档'
        elif action_type == 'activate':
            documents.update(is_active=True)
            message = f'成功激活 {documents.count()} 个文档'
        elif action_type == 'deactivate':
            documents.update(is_active=False)
            message = f'成功停用 {documents.count()} 个文档'
        elif action_type == 'reprocess':
            for document in documents:
                document.status = DocumentStatus.PROCESSING
                document.save()
                DocumentProcessingService.process_document_async(document)
            message = f'成功重新处理 {documents.count()} 个文档'
        
        return Response({'message': message})
    
    @action(detail=False, methods=['get'])
    def search(self, request, *args, **kwargs):
        """搜索文档"""
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['query']
        doc_type = serializer.validated_data.get('type')
        doc_status = serializer.validated_data.get('status')
        page = serializer.validated_data['page']
        page_size = serializer.validated_data['page_size']
        
        queryset = self.get_queryset()
        
        # 搜索条件
        search_q = Q(name__icontains=query) | Q(paragraphs__content__icontains=query)
        if doc_type:
            search_q &= Q(type=doc_type)
        if doc_status:
            search_q &= Q(status=doc_status)
        
        documents = queryset.filter(search_q).distinct()
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        
        results = documents[start:end]
        total = documents.count()
        
        return Response({
            'results': DocumentListSerializer(results, many=True).data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request, *args, **kwargs):
        """获取文档统计"""
        knowledge_base = self.get_knowledge_base()
        serializer = DocumentStatsSerializer(knowledge_base)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def paragraphs(self, request, *args, **kwargs):
        """获取文档段落"""
        document = self.get_object()
        paragraphs = document.paragraphs.all().order_by('position')
        
        page = self.paginate_queryset(paragraphs)
        if page is not None:
            serializer = ParagraphSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ParagraphSerializer(paragraphs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def processing_tasks(self, request, *args, **kwargs):
        """获取文档处理任务"""
        document = self.get_object()
        tasks = document.processing_tasks.all().order_by('-created_at')
        
        serializer = DocumentProcessingTaskSerializer(tasks, many=True)
        return Response(serializer.data)


class ParagraphViewSet(viewsets.ModelViewSet):
    """
    段落管理视图集
    """
    serializer_class = ParagraphSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集"""
        document_id = self.kwargs.get('document_id')
        document = get_object_or_404(
            Document,
            id=document_id,
            created_by=self.request.user
        )
        return document.paragraphs.all().order_by('position')
    
    def get_document(self):
        """获取文档"""
        document_id = self.kwargs.get('document_id')
        return get_object_or_404(
            Document,
            id=document_id,
            created_by=self.request.user
        )
    
    def perform_create(self, serializer):
        """创建段落"""
        document = self.get_document()
        serializer.save(
            document=document,
            knowledge_base=document.knowledge_base
        )
    
    def perform_update(self, serializer):
        """更新段落"""
        paragraph = serializer.save()
        # 更新文档统计
        paragraph.document.update_stats()
    
    def perform_destroy(self, instance):
        """删除段落"""
        document = instance.document
        instance.delete()
        # 更新文档统计
        document.update_stats()
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, *args, **kwargs):
        """切换段落激活状态"""
        paragraph = self.get_object()
        paragraph.is_active = not paragraph.is_active
        paragraph.save()
        
        return Response({
            'message': f'段落已{"激活" if paragraph.is_active else "停用"}',
            'is_active': paragraph.is_active
        })


class ProblemViewSet(viewsets.ModelViewSet):
    """
    问题管理视图集
    """
    serializer_class = ProblemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集"""
        knowledge_base_id = self.kwargs.get('knowledge_base_id')
        knowledge_base = get_object_or_404(
            KnowledgeBase,
            id=knowledge_base_id,
            created_by=self.request.user
        )
        return knowledge_base.problems.all().order_by('-created_at')
    
    def get_knowledge_base(self):
        """获取知识库"""
        knowledge_base_id = self.kwargs.get('knowledge_base_id')
        return get_object_or_404(
            KnowledgeBase,
            id=knowledge_base_id,
            created_by=self.request.user
        )
    
    def perform_create(self, serializer):
        """创建问题"""
        knowledge_base = self.get_knowledge_base()
        serializer.save(knowledge_base=knowledge_base)
    
    @action(detail=False, methods=['get'])
    def search(self, request, *args, **kwargs):
        """搜索问题"""
        query = request.query_params.get('query', '')
        if not query:
            return Response([])
        
        problems = self.get_queryset().filter(
            content__icontains=query
        )[:20]
        
        serializer = self.get_serializer(problems, many=True)
        return Response(serializer.data) 