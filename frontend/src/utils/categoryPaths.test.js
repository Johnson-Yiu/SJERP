import assert from 'node:assert/strict'
import test from 'node:test'
import { categoryContains, categoryTree } from './categoryPaths.js'

test('category cascade merges ancestors and retains same-name leaves under different parents', () => {
  const tree = categoryTree(['电源 / 室内 / 标准', '电源 / 室内 / 标准', '光源 / 室内 / 标准'])
  assert.equal(tree.length, 2)
  assert.equal(tree[0].children.length, 1)
  assert.equal(tree[0].children[0].children.length, 1)
  assert.equal(tree[1].children[0].children[0].value, '光源 / 室内 / 标准')
})

test('parent filtering includes descendants without matching similar names or other branches', () => {
  assert.equal(categoryContains('电源', '电源 / 室内 / 橱柜电源'), true)
  assert.equal(categoryContains('电源 / 室内', '电源/室内/橱柜电源'), true)
  assert.equal(categoryContains('电源 / 室内', '电源 / 室内防水 / 标准'), false)
  assert.equal(categoryContains('电源 / 室内', '光源 / 室内'), false)
  assert.equal(categoryContains('', '光源 / 室内'), true)
})
