import axios from "axios";

export const api = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api` });

export const errorText = (e) => e?.response?.data?.detail || e?.message || "Something went wrong";
