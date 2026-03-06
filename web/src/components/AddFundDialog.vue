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
            <label>搜索基金</label>
            <el-autocomplete
              v-model="searchText"
              :fetch-suggestions="querySearch"
              :trigger-on-focus="false"
              value-key="value"
              placeholder="输入基金代码或名称搜索"
              clearable
              @select="handleSelect"
            >
              <template #default="{ item }">
                <div class="fund-item">
                  <span class="fund-code">{{ item.code }}</span>
                  <span class="fund-name">{{ item.name }}</span>
                  <span class="fund-type">{{ item.type }}</span>
                </div>
              </template>
            </el-autocomplete>
            <span class="hint">支持输入6位代码或基金名称搜索</span>
          </div>

          <div v-if="submitting" class="submitting">
            <span>添加中...</span>
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
import { ElMessage } from 'element-plus';

interface Props {
  visible: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'added'): void;
}>();

interface FundSearchItem {
  code: string;
  name: string;
  type: string;
  value: string;
}

const searchText = ref('');
const selectedFund = ref<FundSearchItem | null>(null);
const submitting = ref(false);
const existingCodes = ref<Set<string>>(new Set());
const searchLoading = ref(false);

const canSubmit = computed(() => {
  if (submitting.value) return false;
  if (!selectedFund.value) return false;
  if (existingCodes.value.has(selectedFund.value.code)) return false;
  return true;
});

async function querySearch(keyword: string, cb: (results: FundSearchItem[]) => void) {
  if (!keyword || keyword.length < 1) {
    cb([]);
    return;
  }

  searchLoading.value = true;

  try {
    const localResult = await fundApi.searchFunds(keyword, 20);
    
    const results: FundSearchItem[] = localResult.funds.map(f => ({
      code: f.code,
      name: f.name,
      type: f.type,
      value: `${f.code} - ${f.name}`,
    }));

    // Use Promise.resolve to ensure callback is called properly in next tick
    Promise.resolve(results).then((data) => cb(data));
  } catch {
    cb([]);
  } finally {
    searchLoading.value = false;
  }
}

function handleSelect(item: FundSearchItem) {
  selectedFund.value = item;
  searchText.value = `${item.code} - ${item.name}`;
}

async function handleSubmit() {
  if (!canSubmit.value || !selectedFund.value) return;

  submitting.value = true;
  try {
    await fundApi.addToWatchlist(selectedFund.value.code, selectedFund.value.name);
    ElMessage.success('添加成功');
    emit('added');
    close();
  } catch (err) {
    console.error('添加基金失败:', err);
    ElMessage.error('添加失败');
  } finally {
    submitting.value = false;
  }
}

function close() {
  emit('close');
  searchText.value = '';
  selectedFund.value = null;
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
  max-width: 480px;
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

.form-group .hint {
  display: block;
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.fund-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.fund-item .fund-code {
  font-size: 12px;
  color: #666;
  min-width: 60px;
}

.fund-item .fund-name {
  flex: 1;
  font-size: 14px;
  color: #fff;
}

.fund-item .fund-type {
  font-size: 12px;
  color: #666;
}

.submitting {
  padding: 12px;
  text-align: center;
  color: #999;
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
  transition: background-color 0.15s ease, border-color 0.15s ease, opacity 0.15s ease;
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

:deep(.el-autocomplete) {
  width: 100%;
}

:deep(.el-input__wrapper) {
  background: #2a2a2a;
  border: 1px solid #2a2a2a;
  box-shadow: none;
}

:deep(.el-input__inner) {
  color: #fff;
}

:deep(.el-input__inner::placeholder) {
  color: #666;
}

:deep(.el-autocomplete__popper) {
  background: #2a2a2a !important;
  border: 1px solid #3a3a3a !important;
}

:deep(.el-autocomplete__popper li) {
  color: #fff;
}

:deep(.el-autocomplete__popper li:hover) {
  background: #3a3a3a;
}
</style>
