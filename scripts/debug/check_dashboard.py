from pathlib import Path
from social_listening.dashboard import load_comments, to_dataframe

path = Path('data/comments_news.jsonl')
comments = load_comments(path)
print('loaded items', len(comments))
df = to_dataframe(comments)
print('dataframe shape', df.shape)
print('columns', list(df.columns))
if not df.empty:
    print('sample article_url:', df['article_url'].head(3).tolist())
    print('fallback stages:', df['fallback_stage'].value_counts().to_dict())
    print('source domains:', df['source_domain'].value_counts().head(10).to_dict())
else:
    print('dataframe is empty')
