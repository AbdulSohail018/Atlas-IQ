-- PostgreSQL initialization script for Glonav
-- This script sets up the initial database schema and extensions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create main database (if not exists)
SELECT 'CREATE DATABASE glonav'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'glonav');

-- Create vector database (if not exists)  
SELECT 'CREATE DATABASE glonav_vectors'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'glonav_vectors');

-- Connect to main database
\c glonav;

-- Enable extensions in main database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create main tables
CREATE TABLE IF NOT EXISTS datasets (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source VARCHAR(255) NOT NULL,
    source_url VARCHAR(500),
    schema_info JSONB,
    record_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    tags JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255) NOT NULL,
    source_url VARCHAR(500),
    document_type VARCHAR(50) DEFAULT 'text',
    language VARCHAR(10) DEFAULT 'en',
    metadata JSONB,
    embedding_id VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    source VARCHAR(255),
    parameters JSONB,
    result JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_queries (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50),
    user_id VARCHAR,
    session_id VARCHAR,
    response JSONB,
    processing_time FLOAT,
    feedback_score INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_datasets_source ON datasets(source);
CREATE INDEX IF NOT EXISTS idx_datasets_active ON datasets(is_active);
CREATE INDEX IF NOT EXISTS idx_datasets_created ON datasets(created_at);
CREATE INDEX IF NOT EXISTS idx_datasets_updated ON datasets(updated_at);

CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_language ON documents(language);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_type ON processing_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created ON processing_jobs(created_at);

CREATE INDEX IF NOT EXISTS idx_user_queries_type ON user_queries(query_type);
CREATE INDEX IF NOT EXISTS idx_user_queries_session ON user_queries(session_id);
CREATE INDEX IF NOT EXISTS idx_user_queries_created ON user_queries(created_at);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_datasets_tags_gin ON datasets USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_datasets_metadata_gin ON datasets USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin ON documents USING GIN(metadata);

-- Connect to vector database
\c glonav_vectors;

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create vector embeddings table
CREATE TABLE IF NOT EXISTS document_embeddings (
    id VARCHAR PRIMARY KEY,
    title VARCHAR(500),
    content TEXT NOT NULL,
    source VARCHAR(255),
    document_type VARCHAR(50) DEFAULT 'text',
    metadata JSONB,
    embedding vector(384),  -- Adjust dimension based on your embedding model
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create vector similarity index
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector 
ON document_embeddings USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Create other indexes
CREATE INDEX IF NOT EXISTS idx_document_embeddings_source ON document_embeddings(source);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_type ON document_embeddings(document_type);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_created ON document_embeddings(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_document_embeddings_updated_at 
    BEFORE UPDATE ON document_embeddings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Back to main database for triggers
\c glonav;

CREATE TRIGGER update_datasets_updated_at 
    BEFORE UPDATE ON datasets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_jobs_updated_at 
    BEFORE UPDATE ON processing_jobs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_queries_updated_at 
    BEFORE UPDATE ON user_queries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data
INSERT INTO datasets (name, description, source, tags, metadata) VALUES
('NYC 311 Service Requests', 'Service requests from NYC 311 system including complaints, inquiries, and service requests', 'NYC Open Data', '["311", "nyc", "services", "complaints"]', '{"update_frequency": "daily", "format": "csv"}'),
('EPA Air Quality Index', 'Daily air quality measurements from EPA monitoring stations across the US', 'EPA', '["air quality", "environment", "epa", "pollution"]', '{"update_frequency": "daily", "format": "api"}'),
('US Census Demographics', 'Population and demographic data from US Census Bureau', 'US Census Bureau', '["demographics", "population", "census"]', '{"update_frequency": "annual", "format": "api"}'),
('WHO Global Health Data', 'Health statistics and indicators from World Health Organization', 'WHO', '["health", "global", "who", "statistics"]', '{"update_frequency": "monthly", "format": "api"}'),
('Climate Change Indicators', 'Long-term climate data and change indicators', 'NOAA', '["climate", "weather", "temperature", "environment"]', '{"update_frequency": "monthly", "format": "api"}')
ON CONFLICT (id) DO NOTHING;

-- Insert sample documents
INSERT INTO documents (title, content, source, document_type, metadata) VALUES
('Air Quality Standards Overview', 'The Clean Air Act requires EPA to set National Ambient Air Quality Standards (NAAQS) for pollutants considered harmful to public health and the environment. The Clean Air Act established two types of national air quality standards...', 'EPA', 'policy', '{"policy_type": "federal", "year": 2023}'),
('NYC 311 Service Guide', '311 provides New Yorkers with one easy-to-remember telephone number for all government information and non-emergency services. Citizens can call 311 to report quality of life issues...', 'NYC Open Data', 'guide', '{"city": "New York", "service_type": "311"}'),
('WHO Global Health Report 2023', 'This report presents the latest data on global health trends, including mortality rates, disease burden, and health system performance indicators across WHO member states...', 'WHO', 'report', '{"year": 2023, "report_type": "annual"}')
ON CONFLICT (id) DO NOTHING;

-- Grant permissions (adjust as needed for your deployment)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;