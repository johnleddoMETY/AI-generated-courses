import axios from "axios";

import { supabase } from "./supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use(async (config) => {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }

  return config;
});

export function createSyllabus({ topic, certification }) {
  return api.post("/syllabus/", { topic, certification });
}

export function createAssessment(syllabusId, { numQuestions = 12, examDate = null } = {}) {
  return api.post(`/syllabus/${syllabusId}/assessment/`, {
    num_questions: numQuestions,
    exam_date: examDate,
  });
}

export function getAssessment(assessmentId) {
  return api.get(`/assessment/${assessmentId}/`);
}

export function gradeAssessment(assessmentId, answers) {
  return api.post(`/assessment/${assessmentId}/grade/`, { answers });
}

export function createRoadmap(assessmentId, { examDate = null } = {}) {
  return api.post(`/assessment/${assessmentId}/roadmap/`, { exam_date: examDate });
}

export function createCourse(roadmapId) {
  return api.post(`/roadmap/${roadmapId}/course/`);
}

export function getCourse(courseId) {
  return api.get(`/course/${courseId}/`);
}

export function regenerateLesson(courseId, itemId) {
  return api.post(`/course/${courseId}/lesson/${itemId}/regenerate/`);
}

export { supabase };
export default api;