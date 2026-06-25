/**
 * 格式化工具函数
 */

/**
 * 格式化时间
 * @param {string|Date} time 时间
 * @param {string} format 格式
 * @returns {string} 格式化后的时间
 */
export const formatTime = (time, format = 'YYYY-MM-DD HH:mm:ss') => {
  if (!time) return '-'
  
  const date = new Date(time)
  if (isNaN(date.getTime())) return '-'
  
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 格式化相对时间
 * @param {string|Date} time 时间
 * @returns {string} 相对时间
 */
export const formatRelativeTime = (time) => {
  if (!time) return '-'
  
  const date = new Date(time)
  if (isNaN(date.getTime())) return '-'
  
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const week = 7 * day
  const month = 30 * day
  const year = 365 * day
  
  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return Math.floor(diff / minute) + '分钟前'
  } else if (diff < day) {
    return Math.floor(diff / hour) + '小时前'
  } else if (diff < week) {
    return Math.floor(diff / day) + '天前'
  } else if (diff < month) {
    return Math.floor(diff / week) + '周前'
  } else if (diff < year) {
    return Math.floor(diff / month) + '个月前'
  } else {
    return Math.floor(diff / year) + '年前'
  }
}

/**
 * 格式化数字
 * @param {number} num 数字
 * @param {number} precision 精度
 * @returns {string} 格式化后的数字
 */
export const formatNumber = (num, precision = 0) => {
  if (num === null || num === undefined || isNaN(num)) return '0'
  
  const number = Number(num)
  
  if (number < 1000) {
    return number.toFixed(precision)
  } else if (number < 1000000) {
    return (number / 1000).toFixed(precision) + 'K'
  } else if (number < 1000000000) {
    return (number / 1000000).toFixed(precision) + 'M'
  } else {
    return (number / 1000000000).toFixed(precision) + 'B'
  }
}

/**
 * 格式化文件大小
 * @param {number} size 文件大小（字节）
 * @param {number} precision 精度
 * @returns {string} 格式化后的文件大小
 */
export const formatFileSize = (size, precision = 1) => {
  if (size === null || size === undefined || isNaN(size)) return '0 B'
  
  const bytes = Number(size)
  
  if (bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(precision)) + ' ' + sizes[i]
}

/**
 * 格式化百分比
 * @param {number} value 值
 * @param {number} total 总数
 * @param {number} precision 精度
 * @returns {string} 百分比字符串
 */
export const formatPercentage = (value, total, precision = 1) => {
  if (!total || total === 0) return '0%'
  
  const percentage = (value / total) * 100
  return percentage.toFixed(precision) + '%'
}

/**
 * 格式化货币
 * @param {number} amount 金额
 * @param {string} currency 货币符号
 * @param {number} precision 精度
 * @returns {string} 格式化后的货币
 */
export const formatCurrency = (amount, currency = '¥', precision = 2) => {
  if (amount === null || amount === undefined || isNaN(amount)) return currency + '0.00'
  
  const number = Number(amount)
  return currency + number.toFixed(precision)
}

/**
 * 格式化手机号
 * @param {string} phone 手机号
 * @returns {string} 格式化后的手机号
 */
export const formatPhone = (phone) => {
  if (!phone) return '-'
  
  const cleaned = phone.replace(/\D/g, '')
  
  if (cleaned.length === 11) {
    return cleaned.replace(/(\d{3})(\d{4})(\d{4})/, '$1****$3')
  }
  
  return phone
}

/**
 * 格式化邮箱
 * @param {string} email 邮箱
 * @returns {string} 格式化后的邮箱
 */
export const formatEmail = (email) => {
  if (!email) return '-'
  
  const [username, domain] = email.split('@')
  if (!username || !domain) return email
  
  if (username.length <= 2) {
    return email
  }
  
  const maskedUsername = username.charAt(0) + '*'.repeat(username.length - 2) + username.charAt(username.length - 1)
  return maskedUsername + '@' + domain
}

/**
 * 格式化文本省略
 * @param {string} text 文本
 * @param {number} maxLength 最大长度
 * @param {string} suffix 后缀
 * @returns {string} 格式化后的文本
 */
export const formatEllipsis = (text, maxLength = 50, suffix = '...') => {
  if (!text) return ''
  
  if (text.length <= maxLength) {
    return text
  }
  
  return text.substring(0, maxLength) + suffix
}

/**
 * 格式化状态
 * @param {string} status 状态
 * @param {Object} statusMap 状态映射
 * @returns {string} 格式化后的状态
 */
export const formatStatus = (status, statusMap = {}) => {
  return statusMap[status] || status
}

/**
 * 格式化数组为字符串
 * @param {Array} array 数组
 * @param {string} separator 分隔符
 * @returns {string} 格式化后的字符串
 */
export const formatArrayToString = (array, separator = ', ') => {
  if (!Array.isArray(array)) return ''
  
  return array.join(separator)
}

/**
 * 格式化对象为查询字符串
 * @param {Object} obj 对象
 * @returns {string} 查询字符串
 */
export const formatObjectToQuery = (obj) => {
  if (!obj || typeof obj !== 'object') return ''
  
  const params = new URLSearchParams()
  
  Object.keys(obj).forEach(key => {
    const value = obj[key]
    if (value !== null && value !== undefined && value !== '') {
      params.append(key, value)
    }
  })
  
  return params.toString()
}

/**
 * 格式化HTML为纯文本
 * @param {string} html HTML字符串
 * @returns {string} 纯文本
 */
export const formatHtmlToText = (html) => {
  if (!html) return ''
  
  // 创建一个临时的div元素
  const tempDiv = document.createElement('div')
  tempDiv.innerHTML = html
  
  // 获取纯文本内容
  return tempDiv.textContent || tempDiv.innerText || ''
}

/**
 * 格式化JSON字符串
 * @param {Object} obj 对象
 * @param {number} space 缩进空格数
 * @returns {string} 格式化后的JSON字符串
 */
export const formatJSON = (obj, space = 2) => {
  try {
    return JSON.stringify(obj, null, space)
  } catch (error) {
    return String(obj)
  }
}

/**
 * 格式化颜色值
 * @param {string} color 颜色值
 * @returns {string} 格式化后的颜色值
 */
export const formatColor = (color) => {
  if (!color) return '#000000'
  
  // 如果是hex颜色值，确保以#开头
  if (/^[0-9A-Fa-f]{6}$/.test(color)) {
    return '#' + color
  }
  
  // 如果已经是完整的hex颜色值
  if (/^#[0-9A-Fa-f]{6}$/.test(color)) {
    return color
  }
  
  // 如果是rgb或rgba格式，直接返回
  if (/^rgba?\(/.test(color)) {
    return color
  }
  
  // 默认返回黑色
  return '#000000'
} 