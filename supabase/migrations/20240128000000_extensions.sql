-- Migration: Enable required PostgreSQL extensions
-- Date: 2024-01-28
-- Description: pgvector for semantic search, PostGIS for geospatial

-- pgvector for product embeddings (Module 1 Scout Engine)
CREATE EXTENSION IF NOT EXISTS vector;

-- PostGIS for routes, locations (Module 5 Time-Chain, Module 9 Portal)
CREATE EXTENSION IF NOT EXISTS postgis;
