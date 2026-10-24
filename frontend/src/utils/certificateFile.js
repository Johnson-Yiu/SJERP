import { apiErrorMessage } from './apiErrors'
export function certificateFileUrl(value) {
  const valueString = String(value || '').trim()
  return valueString.startsWith('/api/media/') ? valueString : ''
}

export function certificateError(error) {
 const labels={name:'证书名称',certificate_no:'证书编号',issuer:'签发机构',product:'所属产品',issued_date:'签发日期',expires_on:'有效期至',file:'证书文件',file_url:'文件链接',notes:'备注'}
 return apiErrorMessage(error).replace(/\b(name|certificate_no|issuer|product|issued_date|expires_on|file|file_url|notes)(?=\s*[:：])/g,key=>labels[key])
}
