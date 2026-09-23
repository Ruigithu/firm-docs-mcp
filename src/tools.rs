//! The MCP tool layer.
//!
//! This is the boundary. Everything below it reads documents; everything above
//! it is a language model deciding what to ask for. The tool descriptions here
//! are not documentation for a human reader, they are the instructions the
//! model acts on, and they are the only lever this server has over how it
//! behaves.

use rmcp::handler::server::wrapper::{Json, Parameters};
use rmcp::model::{ServerCapabilities, ServerConfig};
use rmcp::{ErrorData, ServerHandler, schemars, tool, tool_handler, tool_router};
use serde::{Deserialize, Serialize};

use crate::source::DocumentSource;

fn default_limit() -> usize {
    5
}

#[derive(Debug, Deserialize, schemars::JsonSchema)]
pub struct SearchParams {
    /// What to look for. Terms drawn from the question work better than the
    /// question itself, because this is a text search over the documents, not
    /// a semantic one.
    pub query: String,

    /// Maximum number of documents to return. Five is usually enough; raising
    /// it costs context without improving the choice.
    #[serde(default = "default_limit")]
    pub limit: usize,
}

#[derive(Debug, Deserialize, schemars::JsonSchema)]
pub struct ReadParams {
    /// The document id, exactly as returned by search_documents.
    pub id: String,
}

#[derive(Debug, Serialize, schemars::JsonSchema)]
pub struct SearchHit {
    /// Pass this to read_document.
    pub id: String,
    pub title: String,
    /// A short extract around the first match. Enough to judge relevance, not
    /// enough to answer from.
    pub extract: String,
}

#[derive(Debug, Serialize, schemars::JsonSchema)]
pub struct SearchResults {
    pub matches: Vec<SearchHit>,
    pub count: usize,
}

#[derive(Debug, Serialize, schemars::JsonSchema)]
pub struct DocumentText {
    pub id: String,
    pub title: String,
    pub text: String,
}

/// The MCP server. Holds one document source and exposes it as two tools.
///
/// The source is boxed rather than generic so it can be chosen at startup:
/// the local corpus today, Microsoft Graph next, a fixture in tests. Nothing
/// in this file knows which one it has.
pub struct FirmDocs {
    source: Box<dyn DocumentSource>,
}

#[tool_router]
impl FirmDocs {
    pub fn new(source: Box<dyn DocumentSource>) -> Self {
        Self { source }
    }

    #[tool(
        name = "search_documents",
        description = "Search the firm's legal document library and return the documents most \
likely to contain the answer, each with a short extract showing where the terms matched.\n\n\
The extracts exist so you can choose which document to open. They are a few hundred characters \
taken around the first match and will usually cut off mid-provision, so they are not a basis for \
an answer. Once you have identified the right document, call read_document and work from the full \
text.\n\n\
This is a literal text search, not a semantic one. If nothing relevant comes back, try the terms \
the legislation itself would use rather than the ones in the question."
    )]
    async fn search_documents(
        &self,
        Parameters(SearchParams { query, limit }): Parameters<SearchParams>,
    ) -> Result<Json<SearchResults>, ErrorData> {
        if query.trim().is_empty() {
            return Err(ErrorData::invalid_params("query must not be empty", None));
        }

        let limit = limit.clamp(1, 20);

        let hits = self
            .source
            .search(&query, limit)
            .await
            .map_err(|e| ErrorData::internal_error(e.to_string(), None))?;

        let matches: Vec<SearchHit> = hits
            .into_iter()
            .map(|hit| SearchHit {
                id: hit.id,
                title: hit.title,
                extract: hit.snippet,
            })
            .collect();

        Ok(Json(SearchResults {
            count: matches.len(),
            matches,
        }))
    }

    #[tool(
        name = "read_document",
        description = "Retrieve the full text of one document by its id, as returned by \
search_documents.\n\n\
Read the document before stating a conclusion, and quote the passage the answer rests on, with \
its Article or section number, so the reader can check it against the source.\n\n\
If the document turns out not to contain the answer, say so rather than inferring one. A \
different document may hold it, and search_documents can be called again with different terms."
    )]
    async fn read_document(
        &self,
        Parameters(ReadParams { id }): Parameters<ReadParams>,
    ) -> Result<Json<DocumentText>, ErrorData> {
        let doc = self
            .source
            .read(&id)
            .await
            .map_err(|e| ErrorData::resource_not_found(e.to_string(), None))?;

        Ok(Json(DocumentText {
            id: doc.id,
            title: doc.title,
            text: doc.text,
        }))
    }
}

#[tool_handler]
impl ServerHandler for FirmDocs {
    fn get_info(&self) -> ServerConfig {
        // Both of these are #[non_exhaustive], so they are built by mutation
        // rather than with struct literals: the crate reserves the right to
        // add fields without that being a breaking change.
        let mut info = ServerConfig::default();

        info.capabilities = ServerCapabilities::builder().enable_tools().build();

        info.server_info.name = env!("CARGO_PKG_NAME").to_string();
        info.server_info.version = env!("CARGO_PKG_VERSION").to_string();
        info.server_info.title = Some("Firm Documents".to_string());
        info.server_info.description =
            Some("Search and read the firm's legal document library.".to_string());

        // Server level instructions apply to the whole session rather than to
        // one call, so this is where the working discipline belongs: a tool
        // description can only speak about its own tool.
        info.instructions = Some(
            "This server exposes a library of legal documents. Work in two steps: \
search_documents to find the right document, then read_document to retrieve it in full. \
Do not answer from search extracts.\n\n\
Quote the passage an answer rests on and give its Article or section number, so the reader \
can check it against the source. If the library does not contain the answer, say so; do not \
supply it from memory, because the point of this server is that answers are traceable to \
these documents.\n\n\
These tools retrieve and cite. They do not give legal advice, and a question that calls for \
professional judgement rather than a citation should be answered as such."
                .to_string(),
        );

        info
    }
}
