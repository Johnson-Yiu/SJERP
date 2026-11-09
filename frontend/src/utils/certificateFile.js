import { apiErrorMessage } from './apiErrors'
export function certificateFileUrl(value) {
  const valueString = String(value || '').trim()
  return valueString.startsWith('/api/media/') ? valueString : ''
}

export function certificateError(error) {
 const labels={name:'证书名称',certificate_no:'证书编号',issuer:'签发机构',product:'所属产品',issued_date:'签发日期',expires_on:'有效期至',file:'证书文件',file_url:'文件链接',notes:'备注'}
 const status=Number(error?.status || error?.response?.status || 0)
 const data=error?.data ?? error?.response?.data
 if (status < 500 && data && typeof data === 'object' && !Array.isArray(data)) {
   const messages=Object.entries(data).map(([key,value])=>{
     if (value == null || value === '' || (Array.isArray(value) && !value.length)) return ''
     const message=apiErrorMessage(value)
     return labels[key] ? `${labels[key]}：${message}` : message
   }).filter(Boolean)
   if (messages.length) return [...new Set(messages)].join('；')
 }
 return apiErrorMessage(error)
}
