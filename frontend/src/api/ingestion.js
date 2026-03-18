// src/api/ingestion.js — Ingestion endpoints
import client from './client'

/**
 * Fetch the list of supported CSV sources with their file presence status.
 * Maps to GET /ingest/sources on the FastAPI backend.
 *
 * @returns {Promise<{ sources: Array<{
 *   key: string,
 *   label: string,
 *   filename: string,
 *   domain: string,
 *   present: boolean
 * }> }>}
 */
export function fetchSources() {
  return client.get('/ingest/sources')
}

/**
 * Upload a CSV file for a given source and trigger the full pipeline.
 * Maps to POST /ingest/upload on the FastAPI backend.
 *
 * Sends a multipart/form-data request with two fields:
 * - source: source key (e.g. "musicbuddy")
 * - file: the CSV file blob
 *
 * @param {string} sourceKey - One of: musicbuddy | bookbuddy | goodreads | moviebuddy | letterboxd
 * @param {File} file - The CSV File object from an <input type="file"> or drag-and-drop
 * @param {function(ProgressEvent): void} [onProgress] - Optional upload progress callback
 * @returns {Promise<{
 *   source: string,
 *   filename: string,
 *   ingestion: {
 *     status: string,
 *     ingestion_stdout: string,
 *     ingestion_returncode: number,
 *     dbt_stdout: string,
 *     dbt_returncode: number
 *   }
 * }>}
 */
export function uploadCsv(sourceKey, file, onProgress) {
  const formData = new FormData()
  formData.append('source', sourceKey)
  formData.append('file', file, file.name)

  return client.post('/ingest/upload', formData, {
    headers: {
      // Let the browser set the correct multipart boundary automatically
      'Content-Type': 'multipart/form-data',
    },
    // No timeout for uploads — run_ingestion + dbt run can take several minutes
    timeout: 0,
    onUploadProgress: onProgress ?? undefined,
  })
}
