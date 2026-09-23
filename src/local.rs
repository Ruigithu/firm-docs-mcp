use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use async_trait::async_trait;

use crate::source::{DocRef, Document, DocumentSource};

pub struct LocalFs {
    root: PathBuf,
}

impl LocalFs {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    /// 列出语料目录下所有 .txt 文件。
    fn documents(&self) -> Result<Vec<PathBuf>> {
        let mut out = Vec::new();
        let entries = fs::read_dir(&self.root)
            .with_context(|| format!("读不到目录 {}", self.root.display()))?;
        for entry in entries {
            let path = entry?.path();
            if path.extension().and_then(|e| e.to_str()) == Some("txt") {
                out.push(path);
            }
        }
        out.sort();
        Ok(out)
    }
}

fn title_of(path: &Path) -> String {
    path.file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("untitled")
        .to_string()
}

/// 把字节位置往前挪到最近的字符边界。
///
/// Rust 的字符串切片按字节算,切在多字节字符中间会直接 panic。
/// 语料里有 Coimisiún 这种词,所以这个不是理论问题。
fn floor_boundary(text: &str, mut i: usize) -> usize {
    while i > 0 && !text.is_char_boundary(i) {
        i -= 1;
    }
    i
}

fn snippet_at(text: &str, pos: usize) -> String {
    let start = floor_boundary(text, pos.saturating_sub(120));
    let end = floor_boundary(text, (pos + 200).min(text.len()));
    text[start..end].split_whitespace().collect::<Vec<_>>().join(" ")
}

#[async_trait]
impl DocumentSource for LocalFs {
    async fn search(&self, query: &str, limit: usize) -> Result<Vec<DocRef>> {
        let needle = query.to_lowercase();
        let mut hits = Vec::new();

        for path in self.documents()? {
            let text = fs::read_to_string(&path)
                .with_context(|| format!("读不到 {}", path.display()))?;

            if let Some(pos) = text.to_lowercase().find(&needle) {
                hits.push(DocRef {
                    id: title_of(&path),
                    title: title_of(&path),
                    snippet: snippet_at(&text, pos),
                });
            }

            if hits.len() >= limit {
                break;
            }
        }

        Ok(hits)
    }

    async fn read(&self, id: &str) -> Result<Document> {
            if id.is_empty()
            || id.contains("..")
            || id.contains('/')
            || id.contains('\\')
        {
            anyhow::bail!("invalid document id: {id}");
        }
        let path = self.root.join(format!("{id}.txt"));

        let text = fs::read_to_string(&path)
            .with_context(|| format!("没有 id 为 {id} 的文档"))?;

        Ok(Document {
            id: id.to_string(),
            title: title_of(&path),
            text,
        })
    }
}