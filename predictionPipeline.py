import numpy as np
import pandas as pd
import re
import string
import pickle
from nltk.stem import PorterStemmer

def remove_punctuations(text):
    for punctuation in string.punctuation:
        text = text.replace(punctuation, '')
    return text

def load_model_and_resources():
    try:
        with open('static/model/model_naive.pickle','rb') as f:
            model = pickle.load(f)
        
        with open('static/model/corpora/stopwords/english','r') as file:
            sw = file.read().splitlines()
        
        vocab = pd.read_csv('static/model/vocabulary.txt',header=None)
        tokens = vocab[0].tolist()
        
        return model, sw, tokens
    except FileNotFoundError as e:
        print(f"Error loading resources: {e}")
        print("Please check if all required files exist in the static/model directory")
        return None, None, None

def preprocessing(text, sw):
    data = pd.DataFrame([text], columns=['tweet'])
    data["tweet"] = data["tweet"].apply(lambda x: " ".join(x.lower() for x in x.split()))
    data["tweet"] = data["tweet"].apply(lambda x: " ".join(re.sub(r'^https?:\/\/.*[\r\n]*','',x,flags=re.MULTILINE) for x in x.split()))
    data["tweet"] = data["tweet"].apply(remove_punctuations)
    data["tweet"] = data["tweet"].str.replace('\d+','',regex=True)
    data["tweet"] = data["tweet"].apply(lambda x: " ".join(x for x in x.split() if x not in sw))
    ps = PorterStemmer()
    data["tweet"] = data["tweet"].apply(lambda x: " ".join(ps.stem(x) for x in x.split()))
    return data['tweet']

def vectorizer(ds, vocabulary):
    vectorized_lst = []
    for sentence in ds:
        sentence_lst = np.zeros(len(vocabulary))
        for i in range(len(vocabulary)):
            if vocabulary[i] in sentence.split():
                sentence_lst[i] = 1
        vectorized_lst.append(sentence_lst)
    vectorized_lst_new = np.asarray(vectorized_lst, dtype=np.float32)
    return vectorized_lst_new

def get_prediction(vectorized_text, model):
    prediction = model.predict(vectorized_text)
    if prediction == 0:
        return 'negative'
    if prediction == 1:
        return 'neutral'
    else:
        return 'positive'

def analyze_text(text):
    model, sw, tokens = load_model_and_resources()
    if not all([model, sw, tokens]):
        return "Error: Could not load required resources"
    
    preprocessed_txt = preprocessing(text, sw)
    vectorized_txt = vectorizer(preprocessed_txt, tokens)
    prediction = get_prediction(vectorized_txt, model)
    return prediction

if __name__ == "__main__":
    # Test the pipeline
    test_text = "I have nothing to say"
    result = analyze_text(test_text)
    print(f"Input text: '{test_text}'")
    print(f"Sentiment: {result}")