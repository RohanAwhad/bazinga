import type { ArtifactEntry } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function listArtifacts(projectPath: string): Promise<ArtifactEntry[]> {
  const res = await fetch(`${BASE_URL}/artifacts?project_path=${encodeURIComponent(projectPath)}`);
  if (!res.ok) {
    throw new Error(`listArtifacts failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchArtifact(projectPath: string, path: string): Promise<string> {
  const encodedPath = path.split('/').map(segment => encodeURIComponent(segment)).join('/');
  const res = await fetch(`${BASE_URL}/artifacts/${encodedPath}?project_path=${encodeURIComponent(projectPath)}`);
  if (!res.ok) {
    throw new Error(`fetchArtifact failed: ${res.status} ${res.statusText}`);
  }
  return res.text();
}
