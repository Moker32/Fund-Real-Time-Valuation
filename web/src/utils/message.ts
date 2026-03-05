import { ElMessage } from 'element-plus';

type MessageType = 'success' | 'error' | 'warning' | 'info';

export function message(type: MessageType, message: string, duration = 3000) {
  ElMessage({
    message,
    type,
    duration,
  });
}

export const toast = {
  success(message: string, duration?: number) {
    return message('success', message, duration);
  },
  error(message: string, duration = 5000) {
    return message('error', message, duration);
  },
  warning(message: string, duration?: number) {
    return message('warning', message, duration);
  },
  info(message: string, duration?: number) {
    return message('info', message, duration);
  },
};
