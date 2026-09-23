<script setup>
import { CalendarDays } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({ modelValue: { type: String, default: '' }, required: Boolean, withTime: Boolean })
const emit = defineEmits(['update:modelValue'])
const year = ref(''), month = ref(''), day = ref(''), hour = ref(''), minute = ref('')
const monthInput = ref(null), dayInput = ref(null), hourInput = ref(null), minuteInput = ref(null), picker = ref(null)

function setParts(value) {
  const [datePart = '', timePart = ''] = (value || '').split('T')
  const [nextYear = '', nextMonth = '', nextDay = ''] = datePart.split('-')
  const [nextHour = '', nextMinute = ''] = timePart.split(':')
  year.value = nextYear
  month.value = nextMonth
  day.value = nextDay
  hour.value = nextHour
  minute.value = nextMinute
}
watch(() => props.modelValue, setParts, { immediate: true })

function digits(value, length) { return String(value || '').replace(/\D/g, '').slice(0, length) }
function validDate() {
  if (!/^\d{4}$/.test(year.value) || !/^\d{2}$/.test(month.value) || !/^\d{2}$/.test(day.value)) return false
  const value = `${year.value}-${month.value}-${day.value}`
  const date = new Date(`${value}T00:00:00`)
  return !Number.isNaN(date.valueOf()) && date.getFullYear() === Number(year.value) && date.getMonth() + 1 === Number(month.value) && date.getDate() === Number(day.value)
}
const completeValue = computed(() => {
  if (!validDate()) return ''
  const date = `${year.value}-${month.value}-${day.value}`
  if (!props.withTime) return date
  return /^\d{2}$/.test(hour.value) && /^\d{2}$/.test(minute.value) && Number(hour.value) < 24 && Number(minute.value) < 60
    ? `${date}T${hour.value}:${minute.value}`
    : ''
})

function emitValue() {
  if (completeValue.value) emit('update:modelValue', completeValue.value)
  // Clear optional values immediately when the visible value is incomplete.
  // Keeping the previous value made a cleared date submit as stale data.
  else emit('update:modelValue', '')
}
function onYearInput() {
  year.value = digits(year.value, 4)
  if (year.value.length === 4) nextTick(() => monthInput.value?.focus())
  emitValue()
}
function onMonthInput() {
  month.value = digits(month.value, 2)
  if (month.value.length === 2) nextTick(() => dayInput.value?.focus())
  emitValue()
}
function onDayInput() {
  day.value = digits(day.value, 2)
  if (day.value.length === 2 && props.withTime) nextTick(() => hourInput.value?.focus())
  emitValue()
}
function onHourInput() {
  hour.value = digits(hour.value, 2)
  if (hour.value.length === 2) nextTick(() => minuteInput.value?.focus())
  emitValue()
}
function onMinuteInput() { minute.value = digits(minute.value, 2); emitValue() }
function openPicker() {
  try { picker.value?.showPicker() }
  catch { picker.value?.focus() }
}
function applyPickerValue(event) { emit('update:modelValue', event.target.value) }
</script>

<template>
  <div class="segmented-date">
    <input v-model="year" class="date-year" inputmode="numeric" maxlength="4" :required="required" aria-label="年份" @input="onYearInput" @focus="$event.target.select()" />
    <span>/</span>
    <input ref="monthInput" v-model="month" inputmode="numeric" maxlength="2" aria-label="月份" @input="onMonthInput" @focus="$event.target.select()" />
    <span>/</span>
    <input ref="dayInput" v-model="day" inputmode="numeric" maxlength="2" aria-label="日期" @input="onDayInput" @focus="$event.target.select()" />
    <span v-if="withTime" class="time-group" aria-label="时间">
      <input ref="hourInput" v-model="hour" inputmode="numeric" maxlength="2" aria-label="小时" @input="onHourInput" @focus="$event.target.select()" />
      <b aria-hidden="true">:</b>
      <input ref="minuteInput" v-model="minute" inputmode="numeric" maxlength="2" aria-label="分钟" @input="onMinuteInput" @focus="$event.target.select()" />
    </span>
    <span class="date-spacer" aria-hidden="true" />
    <button type="button" aria-label="打开日期选择器" @click="openPicker"><CalendarDays :size="16" /></button>
    <input ref="picker" class="native-date-picker" :type="withTime ? 'datetime-local' : 'date'" :value="modelValue" tabindex="-1" @change="applyPickerValue" />
  </div>
</template>

<style scoped>
.segmented-date{position:relative;display:flex;align-items:center;height:40px;border:1px solid #d2ddd8;border-radius:7px;background:#fff;padding:0 10px;color:#173e35}.segmented-date:focus-within{border-color:#4f9f8e;box-shadow:0 0 0 3px #4f9f8e1f}.segmented-date input:not(.native-date-picker){flex:0 0 auto;min-width:0;border:0!important;border-radius:0!important;box-shadow:none!important;outline:0;padding:0;background:transparent;font:inherit;line-height:1.25;text-align:left;color:inherit;appearance:none}.segmented-date input.date-year{width:3.6ch!important}.segmented-date input:not(.date-year):not(.native-date-picker){width:2ch!important}.segmented-date span{flex:0 0 auto;color:#405b53}.segmented-date .time-group{display:flex;align-items:center;gap:0;margin-left:8px}.segmented-date .time-group input:not(.native-date-picker){width:1.7ch!important;text-align:center}.segmented-date .time-group b{margin:0 -1px;font-weight:500;color:#405b53}.segmented-date .date-spacer{flex:1 1 auto}.segmented-date button{flex:0 0 auto;margin-left:0;border:0;background:transparent;color:#182f2a;display:grid;place-items:center;padding:5px 0 5px 8px;cursor:pointer}.segmented-date button:hover{color:#0d5d4d}.segmented-date button:focus-visible{outline:2px solid #4f9f8e;outline-offset:2px;border-radius:3px}.native-date-picker{position:absolute;inline-size:1px;block-size:1px;opacity:0;pointer-events:none}.segmented-date input:not(.date-year):not(.native-date-picker){width:2.2ch!important}.segmented-date .time-group{gap:2px;margin-left:10px}.segmented-date .time-group input:not(.native-date-picker){width:2.3ch!important;padding:0 1px!important}.segmented-date .time-group b{margin:0;font-weight:600}
</style>
