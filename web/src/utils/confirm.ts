import { ElMessageBox } from 'element-plus';

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'warning' | 'info' | 'success' | 'error';
}

export async function confirm(options: ConfirmOptions): Promise<boolean> {
  try {
    await ElMessageBox.confirm(options.message, options.title || '确认操作', {
      confirmButtonText: options.confirmText || '确认',
      cancelButtonText: options.cancelText || '取消',
      type: options.type || 'warning',
    });
    return true;
  } catch {
    return false;
  }
}
