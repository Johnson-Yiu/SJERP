import { defineConfig } from '@playwright/test'
import path from 'node:path'
const root = process.cwd()
export default defineConfig({ testDir: path.join(root,'browser-tests'), testMatch:'workspace-tabs-real.spec.js', workers:1, retries:0, reporter:'list', outputDir:path.resolve(root,'../docs/uat-evidence/internal-workspace-tabs-20261105/manual-chrome/artifacts'), use:{baseURL:'http://127.0.0.1:5196',channel:'chrome',viewport:{width:1440,height:1000},screenshot:'only-on-failure'} })
