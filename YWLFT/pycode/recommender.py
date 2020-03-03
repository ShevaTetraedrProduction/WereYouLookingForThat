import pandas as pd
import psycopg2 as ps2
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

ds = pd.read_csv("sample-data.csv")

#tfidf

tf = TfidfVectorizer(analyzer='word', ngram_range=(1, 3), min_df=0, stop_words='english')
tfidf_matrix = tf.fit_transform(ds['description'])

cosine_similarities = linear_kernel(tfidf_matrix, tfidf_matrix)

results = {}

for idx, row in ds.iterrows():
    similar_indices = cosine_similarities[idx].argsort()[:-100:-1]
    similar_items = [(cosine_similarities[idx][i], ds['id'][i]) for i in similar_indices]

    results[row['id']] = similar_items[1:]
print('done!')

#DB stemming and counting
conn = ps2.connect("dbname = FirstDB user=postgres password = 54321")
cur = conn.cursor()

stemer = PorterStemmer()
stem_cache = {}

stem_count = Counter()

def get_stem(token):
    stem = stem_cache.get(token, None)
    if stem:
        return stem
    token = token.lower()
    stem = stemer.stem(token)
    stem_cache[token] = stem
    return stem


def count_unique_tokens_in_question(ques):
    stem_count = Counter()
    for tweet_series in ques:
        tweet = tweet_series
        tokens = word_tokenize(tweet)
        for token in tokens:
            stem = get_stem(token)
            stem_count[stem] += 1
    return stem_count

#print recommendation

def item(id):
    return ds.loc[ds['id'] == id]['description'].tolist()[0].split(' - ')[0]

def recommend(item_id, user_id):

    recs = results[item_id][:2]
    for rec in recs:
        print("Recommended: "+ str(user_id) + ' ' + item(rec[1]))
        st = str(item(rec[1]))
        cur.execute("insert into recommend values (%s, %s);", (user_id, st))
    conn.commit()
    cur.execute("CREATE TABLE foo AS (SELECT DISTINCT * FROM recommend);  DROP TABLE recommend; ALTER TABLE foo RENAME TO recommend;")
    cur.execute("SELECT * FROM recommend ORDER BY uid ASC")
    conn.commit()

def users_recomm(id_user, st_count):
    dt = {k: v for k, v in sorted(dict(st_count).items(), key=lambda item: item[1])[::-1]}
    list_pw = [x for x in dt.keys()][:5]
    ls = []
    for j in range(1, len(ds['id']+1)):
        st = item(j)
        for x in list_pw:
            if x in st:
                ls.append(j)
                list_pw.remove(x)
            continue
    for j in ls:
        recommend(item_id = j, user_id = id_user)

cur.execute("select * from us")
q = cur.fetchall()
conn.commit()

id_users = {i[0] for i in q}

for i in id_users:
    string_to_stem = [x[1] for x in q if x[0] == i]
    st_count = count_unique_tokens_in_question(string_to_stem)
    users_recomm(i, st_count)