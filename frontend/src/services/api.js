import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
});

export async function generateLearningPath(data) {
  // Temporary mock response.
  // Replace this with the real backend API later.

  return {
    data: {
      assessmentId: "123",
      message: "Assessment generated successfully",
      certification: data.certification,
      topic: data.topic,
    },
  };

  /*
  Real backend call later:

  return api.post("/learn", data);

  */
}

export default api;