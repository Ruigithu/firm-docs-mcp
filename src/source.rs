use anyhow::Result;
use async_trait::async_trait;

/// 搜索返回的文档指针。故意做得很轻:搜索结果会进入模型的
/// 上下文,所以只带摘要,不带正文。
#[derive(Debug, Clone)]
pub struct DocRef {
    pub id: String,
    pub title: String,
    pub snippet: String,
}

/// 一份文档的完整内容,由 read 返回。
#[derive(Debug, Clone)]
pub struct Document {
    pub id: String,
    pub title: String,
    pub text: String,
}

/// 任何能被搜索和读取的文档来源。
///
/// 本地文件夹、Microsoft Graph、测试用的假数据,都实现这一个接口。
/// 工具层只认这个 trait,不知道背后是谁。
#[async_trait]
pub trait DocumentSource: Send + Sync {
    async fn search(&self, query: &str, limit: usize) -> Result<Vec<DocRef>>;
    async fn read(&self, id: &str) -> Result<Document>;
}