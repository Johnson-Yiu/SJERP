import {defineConfig} from '@playwright/test'
import base from './playwright.config.js'
export default defineConfig({...base,use:{...base.use,baseURL:'http://127.0.0.1:5210'},webServer:undefined})
