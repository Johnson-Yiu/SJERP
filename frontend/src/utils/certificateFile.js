import { apiErrorMessage } from './apiErrors'
export function certificateFileUrl(value) {
  try { const url = new URL(String(value || '').trim()); return ['http:', 'https:'].includes(url.protocol) ? url.href : '' } catch { return '' }
}

export function certificateError(error) {
 const labels={name:'证书名称',certificate_no:'证书编号',issuer:'签发机构',product:'所属产品',issued_date:'签发日期',expires_on:'有效期至',file_url:'文件链接',notes:'备注'}
 return apiErrorMessage(error).replace(/\b(name|certificate_no|issuer|product|issued_date|expires_on|file_url|notes)(?=\s*[:：])/g,key=>labels[key])
}
