import { apiErrorMessage } from './apiErrors'

const fields = {
  name: '名称', supplier: '供应商', unit: '交易单位', factor: '换算系数',
  carton_length: '箱长', carton_width: '箱宽', carton_height: '箱高',
  carton_tare_weight: '外箱皮重', partial_carton_policy: '尾货策略',
  allow_fraction: '小数规则', qty_per_carton_override: '每箱基础数量',
  unit_net_weight: '单件净重', packaging_template: '包装模板',
}

// Translate validation field labels only; leave the server's rejection unchanged.
export function packagingError(error) {
  return apiErrorMessage(error).replace(/\b([a-z_]+)(?=\s*[:：])/g, key => fields[key] || key)
}
