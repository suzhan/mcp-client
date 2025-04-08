/**
 * 日期时间格式化工具函数
 */

/**
 * 格式化日期为友好显示格式
 * @param date 要格式化的日期
 * @returns 格式化后的日期字符串
 */
export function formatDate(date: Date): string {
  if (!date) return '';

  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  // 如果是今天内的时间，显示具体时间
  if (diff < 24 * 60 * 60 * 1000 && 
      date.getDate() === now.getDate() &&
      date.getMonth() === now.getMonth() &&
      date.getFullYear() === now.getFullYear()) {
    return `今天 ${formatTime(date)}`;
  }
  
  // 如果是昨天的时间
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.getDate() === yesterday.getDate() &&
      date.getMonth() === yesterday.getMonth() &&
      date.getFullYear() === yesterday.getFullYear()) {
    return `昨天 ${formatTime(date)}`;
  }

  // 如果是今年内的时间
  if (date.getFullYear() === now.getFullYear()) {
    return `${padZero(date.getMonth() + 1)}-${padZero(date.getDate())} ${formatTime(date)}`;
  }
  
  // 其他情况，显示完整日期
  return `${date.getFullYear()}-${padZero(date.getMonth() + 1)}-${padZero(date.getDate())} ${formatTime(date)}`;
}

/**
 * 格式化时间部分
 * @param date 日期对象
 * @returns 格式化后的时间字符串 (HH:mm)
 */
function formatTime(date: Date): string {
  return `${padZero(date.getHours())}:${padZero(date.getMinutes())}`;
}

/**
 * 数字补零
 * @param num 要补零的数字
 * @returns 补零后的字符串
 */
function padZero(num: number): string {
  return num < 10 ? `0${num}` : `${num}`;
}

/**
 * 格式化为ISO日期时间
 * @param date 日期对象
 * @returns ISO格式的日期时间字符串
 */
export function formatISODate(date: Date): string {
  if (!date) return '';
  return date.toISOString();
}

/**
 * 计算相对时间（多久之前）
 * @param date 日期对象
 * @returns 相对时间描述
 */
export function timeAgo(date: Date): string {
  if (!date) return '';
  
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  // 转换为秒
  const seconds = Math.floor(diff / 1000);
  
  // 小于1分钟
  if (seconds < 60) {
    return '刚刚';
  }
  
  // 小于1小时
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}分钟前`;
  }
  
  // 小于1天
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}小时前`;
  }
  
  // 小于30天
  const days = Math.floor(hours / 24);
  if (days < 30) {
    return `${days}天前`;
  }
  
  // 小于12个月
  const months = Math.floor(days / 30);
  if (months < 12) {
    return `${months}个月前`;
  }
  
  // 大于等于12个月
  const years = Math.floor(months / 12);
  return `${years}年前`;
} 