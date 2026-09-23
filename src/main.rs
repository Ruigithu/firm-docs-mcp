mod local;
mod source;
mod tools;

use std::path::PathBuf;

use anyhow::{Context, Result};
use rmcp::ServiceExt;
use rmcp::transport::stdio;

use local::LocalFs;
use tools::FirmDocs;

/// Where the corpus lives.
///
/// This cannot be a relative path in practice. An MCP server is launched as a
/// child process by its client, with a working directory the server does not
/// choose, so "corpus" resolves somewhere unpredictable. The path is read from
/// the environment and the client is configured to supply it.
fn corpus_path() -> Result<PathBuf> {
    let raw = std::env::var("FIRM_DOCS_CORPUS")
        .context("FIRM_DOCS_CORPUS is not set: it must name the corpus directory")?;
    let path = PathBuf::from(raw);
    if !path.is_dir() {
        anyhow::bail!("FIRM_DOCS_CORPUS is not a directory: {}", path.display());
    }
    Ok(path)
}

#[tokio::main]
async fn main() -> Result<()> {
    // stdout carries the MCP protocol. Anything printed there corrupts the
    // stream, so diagnostics go to stderr, which the client shows in its logs.
    let corpus = corpus_path()?;
    eprintln!("firm-docs-mcp: serving {}", corpus.display());

    let source = Box::new(LocalFs::new(corpus));
    let service = FirmDocs::new(source)
        .serve(stdio())
        .await
        .context("failed to start the MCP server on stdio")?;

    service.waiting().await?;
    Ok(())
}
