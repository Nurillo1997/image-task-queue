const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function uploadImage(file, operation) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("operation", operation);

  const response = await fetch(`${API_BASE_URL}/api/v1/images/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || "Yuklashda xatolik yuz berdi");
  }

  return response.json();
}

export async function getTaskStatus(taskId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/images/status/${taskId}`);
  if (!response.ok) {
    throw new Error("Status olinmadi");
  }
  return response.json();
}

export function getResultUrl(taskId) {
  return `${API_BASE_URL}/api/v1/images/result/${taskId}`;
}
