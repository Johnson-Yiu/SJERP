<script setup>
import { certificateBadge } from '../utils/certificateExpiry'
defineProps({ certificate: { type: Object, required: true } })
</script>
<template><span class="certificate-expiry-badge" :class="certificate.expiry_status">{{ certificateBadge(certificate) }}</span></template>
<style scoped>
.certificate-expiry-badge{display:inline-block;padding:4px 8px;border-radius:6px;font-size:var(--text-caption);white-space:nowrap;background:#eef2f0;color:#62736b}.expired{background:#fce9e7;color:#a43932}.expiring_30{background:#fff0db;color:#995409}.expiring_90{background:#fff7de;color:#806625}.valid{background:#e7f3ec;color:#2d7051}
</style>
