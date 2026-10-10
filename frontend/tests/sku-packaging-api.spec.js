import { expect, it } from 'vitest'
import { api } from '../src/api'

it('preserves concrete nested packaging validation errors through the API interceptor', async () => {
  const adapter = async config => {
    throw { config, response: { status: 400, data: { packaging_profile_input: { qty_per_carton_override: ['每箱数量必须大于 0。'] } } } }
  }
  await expect(api.post('/skus/batch-create/', { items: [] }, { adapter })).rejects.toThrow('每箱数量必须大于 0。')
})
