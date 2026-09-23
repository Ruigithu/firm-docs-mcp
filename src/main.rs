mod local;
mod source;

use anyhow::Result;
use local::LocalFs;
use source::DocumentSource;

#[tokio::main]
async fn main() -> Result<()> {
    let source = LocalFs::new("corpus");

    let hits = source.search("72 hours", 5).await?;
    for hit in &hits {
        println!("[{}]", hit.id);
        println!("    {}\n", hit.snippet);
    }
    println!("{} 条结果", hits.len());

    let doc = source.read("gdpr").await?;
    println!("{} : {} 字符", doc.title, doc.text.chars().count());

    let bad = source.read("../Cargo").await;
    println!("{:?}", bad);

    Ok(())
}