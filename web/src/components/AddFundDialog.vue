<template>
  <Transition name="dialog">
    <div v-if="visible" class="dialog-overlay" @click.self="close">
      <div class="dialog add-fund-dialog">
        <div class="dialog-header">
          <h3>添加基金</h3>
          <button class="close-btn" @click="close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="dialog-body">
          <div class="form-group">
            <label>基金代码</label>
            <input
              v-model="form.code"
              type="text"
              placeholder="例如: 161039"
              maxlength="6"
              @input="onCodeInput"
            />
            <span class="hint">请输入6位数字基金代码</span>
          </div>

          <div class="form-group">
            <label>基金名称</label>
            <input
              v-model="form.name"
              type="text"
              placeholder="例如: 易方达消费行业股票"
            />
          </div>

          <div v-if="searchResult" class="search-result">
            <div class="result-item">
              <div class="fund-info">
                <span class="fund-code">{{ searchResult.code }}</span>
                <span class="fund-name">{{ searchResult.name }}</span>
              </div>
            </div>
          </div>

          <div v-if="searchLoading" class="search-loading">
            <span>正在查询基金信息...</span>
          </div>

          <div v-if="searchError" class="search-error">
            {{ searchError }}
          </div>
        </div>

        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="close">取消</button>
          <button
            class="btn btn-primary"
            :disabled="!canSubmit || submitting"
            @click="handleSubmit"
          >
            {{ submitting ? '添加中...' : '添加' }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { fundApi } from '@/api';
import type { Fund } from '@/types';

interface Props {
  visible: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'added'): void;
}>();

const form = ref({
  code: '',
  name: '',
});

const searchResult = ref<Fund | null>(null);
const searchLoading = ref(false);
const searchError = ref<string | null>(null);
const submitting = ref(false);
const existingCodes = ref<Set<string>>(new Set());

const isInWatchlist = computed(() => {
  if (!searchResult.value) return false;
  return existingCodes.value.has(searchResult.value.code);
});

const canSubmit = computed(() => {
  if (submitting.value) return false;
  if (!form.value.code || form.value.code.length !== 6) return false;
  if (!form.value.name) return false;
  if (searchError.value) return false;
  if (isInWatchlist.value) return false;
  return true;
});

async function searchFund(code: string) {
  if (code.length !== 6) {
    searchResult.value = null;
    searchError.value = null;
    return;
  }

  searchLoading.value = true;
  searchError.value = null;

  try {
    const fund = await fundApi.getFund(code);
    searchResult.value = fund;
    form.value.name = fund.name;
  } catch (err: unknown) {
    const axiosError = err as { response?: { data?: { detail?: string } } };
    searchResult.value = null;
    searchError.value = axiosError.response?.data?.detail || '未找到该基金';
  } finally {
    searchLoading.value = false;
  }
}

function onCodeInput() {
  form.value.code = form.value.code.replace(/\D/g, '');
  searchFund(form.value.code);
}

async function handleSubmit() {
  if (!canSubmit.value) return;

  submitting.value = true;
  try {
    await fundApi.addToWatchlist(form.value.code, form.value.name);
    emit('added');
    close();
  } catch (err) {
    console.error('添加基金失败:', err);
  } finally {
    submitting.value = false;
  }
}

function close() {
  emit('close');
  setTimeout(() => {
    form.value = { code: '', name: '' };
    searchResult.value = null;
    searchError.value = null;
  }, 200);
}

watch(() => props.visible, async (visible) => {
  if (visible) {
    try {
      const response = await fundApi.getFunds();
      existingCodes.value = new Set(response.funds.map((f: Fund) => f.code));
    } catch (err) {
      console.error('获取基金列表失败:', err);
    }
  }
});
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  width: 90%;
  max-width: 420px;
  background: #1e1e1e;
  border-radius: 12px;
  border: 1px solid #2a2a2a;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.dialog-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #999;
  cursor: pointer;
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

.dialog-body {
  padding: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  color: #999;
  margin-bottom: 4px;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  background: #2a2a2a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  color: #fff;
  font-size: 16px;
}

.form-group input:focus {
  outline: none;
  border-color: #1890ff;
}

.form-group .hint {
  display: block;
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.search-result {
  margin-top: 16px;
}

.result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: #2a2a2a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
}

.fund-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.fund-code {
  font-size: 12px;
  color: #666;
}

.fund-name {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
}

.search-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  margin-top: 16px;
  background: #2a2a2a;
  border-radius: 8px;
  color: #999;
  font-size: 14px;
}

.search-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  margin-top: 16px;
  background: rgba(82, 196, 26, 0.15);
  color: #52c41a;
  border-radius: 8px;
  font-size: 14px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #2a2a2a;
  border: 1px solid #2a2a2a;
  color: #fff;
}

.btn-secondary:hover:not(:disabled) {
  background: #3a3a3a;
}

.btn-primary {
  background: #1890ff;
  border: 1px solid #1890ff;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

/* Transitions */
.dialog-enter-active,
.dialog-leave-active {
  transition: all 0.2s ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .dialog,
.dialog-leave-to .dialog {
  transform: scale(0.95);
}
</style>
