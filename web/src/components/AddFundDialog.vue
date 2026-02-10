<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-overlay" @click.self="close">
      <div class="dialog add-fund-dialog">
        <div class="dialog-header">
          <h3>{{ isEditing ? '编辑基金' : '添加基金' }}</h3>
          <button class="close-btn" @click="close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="dialog-body">
          <div class="form-group">
            <label for="fundCode">基金代码</label>
            <input
              id="fundCode"
              v-model="form.code"
              type="text"
              placeholder="例如: 161039"
              maxlength="6"
              :disabled="isEditing"
              @input="onCodeInput"
            />
            <span class="hint">请输入6位数字基金代码</span>
          </div>

          <div class="form-group">
            <label for="fundName">基金名称</label>
            <input
              id="fundName"
              v-model="form.name"
              type="text"
              placeholder="例如: 易方达消费行业股票"
            />
          </div>

          <div v-if="searchResult" class="search-result">
            <div class="result-item" :class="{ selected: isInWatchlist }">
              <div class="fund-info">
                <span class="fund-code">{{ searchResult.code }}</span>
                <span class="fund-name">{{ searchResult.name }}</span>
              </div>
              <span v-if="isInWatchlist" class="status-badge">已在自选</span>
            </div>
          </div>

          <div v-if="searchLoading" class="search-loading">
            <div class="spinner"></div>
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
            <span v-if="submitting" class="spinner"></span>
            {{ submitting ? '添加中...' : (isEditing ? '保存' : '添加') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { fundApi } from '@/api';
import type { Fund } from '@/types';

interface Props {
  visible: boolean;
  editFund?: Fund | null;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  editFund: null,
});

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

const isEditing = computed(() => !!props.editFund);

// 检查是否已在自选列表中
const isInWatchlist = computed(() => {
  if (!searchResult.value) return false;
  return existingCodes.value.has(searchResult.value.code);
});

const canSubmit = computed(() => {
  if (submitting.value) return false;
  if (!form.value.code || form.value.code.length !== 6) return false;
  if (!form.value.name) return false;
  if (searchError.value) return false;
  // 编辑模式不需要检查是否在列表中
  if (isEditing.value) return true;
  // 添加模式下如果在列表中则不允许添加
  if (isInWatchlist.value) return false;
  return true;
});

// 搜索基金
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
  // 只保留数字
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
  // 重置表单
  setTimeout(() => {
    form.value = { code: '', name: '' };
    searchResult.value = null;
    searchError.value = null;
  }, 200);
}

// 监听编辑基金
watch(() => props.editFund, (fund) => {
  if (fund) {
    form.value = { code: fund.code, name: fund.name };
    searchResult.value = fund;
    searchError.value = null;
  }
}, { immediate: true });

// 获取现有基金代码列表
watch(() => props.visible, async (visible) => {
  if (visible) {
    try {
      const response = await fundApi.getFunds();
      existingCodes.value = new Set(response.funds.map((f: Fund) => f.code));
    } catch (err) {
      console.error('获取基金列表失败:', err);
    }
  }
}, { immediate: true });
</script>

<style lang="scss" scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn var(--transition-fast);
}

.add-fund-dialog {
  width: 90%;
  max-width: 420px;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-divider);

  h3 {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
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
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);

    svg {
      width: 20px;
      height: 20px;
    }

    &:hover {
      background: var(--color-bg-tertiary);
      color: var(--color-text-primary);
    }
  }
}

.dialog-body {
  padding: var(--spacing-lg);
}

.form-group {
  margin-bottom: var(--spacing-lg);

  label {
    display: block;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-xs);
  }

  input {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-bg-tertiary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-primary);
    font-size: var(--font-size-md);
    transition: all var(--transition-fast);

    &::placeholder {
      color: var(--color-text-tertiary);
    }

    &:focus {
      outline: none;
      border-color: var(--color-primary);
      box-shadow: 0 0 0 3px var(--color-primary-alpha);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  .hint {
    display: block;
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    margin-top: var(--spacing-xs);
  }
}

.search-result {
  margin-top: var(--spacing-md);
}

.result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &.selected {
    border-color: var(--color-warning);
    background: var(--color-warning-alpha);
  }

  .fund-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .fund-code {
    font-size: var(--font-size-xs);
    color: var(--color-text-tertiary);
    font-family: var(--font-mono);
  }

  .fund-name {
    font-size: var(--font-size-sm);
    color: var(--color-text-primary);
    font-weight: var(--font-weight-medium);
  }

  .status-badge {
    font-size: var(--font-size-xs);
    padding: 2px 8px;
    background: var(--color-warning-alpha);
    color: var(--color-warning);
    border-radius: var(--radius-full);
  }
}

.search-loading,
.search-error {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  margin-top: var(--spacing-md);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
}

.search-loading {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.search-error {
  background: var(--color-fall-alpha);
  color: var(--color-fall);
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-top: 1px solid var(--color-divider);
}

.btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .spinner {
    width: 14px;
    height: 14px;
  }
}

.btn-secondary {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);

  &:hover:not(:disabled) {
    background: var(--color-bg-card);
    border-color: var(--color-border-light);
  }
}

.btn-primary {
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  color: white;

  &:hover:not(:disabled) {
    opacity: 0.9;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
