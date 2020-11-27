#import libraries:
import pandas as pd
import numpy as np
import json
import os
import io
import subprocess
import random
import logging
from sklearn.metrics import classification_report
from sklearn.metrics import precision_recall_fscore_support
from spacy.scorer import Scorer
from sklearn.metrics import accuracy_score
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFSyntaxError
import nltk
from nltk.corpus import stopwords
import spacy
from string import punctuation
import docx2txt
from difflib import SequenceMatcher

#add list Labels:
LABELS = ['job title','ville','missions','experience','contrat','formation']
PATH_WORD= "./train_data/Word"
PATH_PDF= "./train_data/PDF"
# create blank Language class
nlp = spacy.blank('fr')
#Annotation Dic
Dic={
    "Droit français":["droit des contrats","droit commercial","droit des garanties","droit fiscal des entreprises",
                      "droit patrimonial","régime matrimonial","succession","droit bancaire"],
    "Droit bancaire":["FBF","ISDA","Normes comptables","IFRS","AAP","Droit financier","code monétaire et financier", "CMF"],
    "Produits bancaires":["produits dérivés", "instruments financiers" , "produit d’investissement",
"produits de placement","produit de spéculation","instrument de marchés","produits structurés","produits d’épargne" , "produits d’assurance","émissions obligataires" , "titres de créance",
"Opérations de marché","Marchés financiers"],
    "Fiscalité":["l’impôt sur le revenu" , "IR" ,"l'impôt sur les sociétés" ,"IS","impôts sur les bénéfices",
"l’impôt de solidarité sur la fortune","ISF","la taxe sur la valeur ajoutée","TVA","la taxe intérieure sur les produits pétroliers",
                 "TIPP","code général des impôts","CGI","taxes","CGS","CRDS"],
    "Risque bancaire":["risque de marché","risque opérationnel", "risque de contrepartie","risque de crédit",
        "Normes de réglementation","FRTB","BALE2","BALE 2.5","EMIR","VAR","LCR","CVAR","Expected Shortfall","ES"],
    "Outils informatiques":["Microsoft Office","Excel","Outlook","Access","VBA","Word","bureautique"],
    "Organisation":["Agenda","Rigueur","planifier","Travail en équipe","Outlook"],
    "Communication":["Convaincre","Relationnel","collaboration","réunions","compte rendu","Anglais Ecrit" , "Oral"]     
}

def convert_annotation(df):
    '''
    Returns an annotated list of each row in the dataframe df

            Parameters:
                    df (Dataframe): a Pandas.Dataframe
            Returns:
                    binary_sum (str): Binary string of the sum of a and b
    '''
    train_data = []
    for _, row in df.iterrows():
        content = convertTopdf(PATH_PDF + '/' + row.file).lower()
        content = " ".join(content.split())
        print(row.file)
        entities = extract_info(content, row.text.lower())
        train_data.append((content, {"entities":entities}))
    return train_data

#convert files pdf to text:
def convertTopdf(fname, pages=None):
    '''
    Returns a PDF file converted to a text format

            Parameters:
                    fname (string): A string representing the file name
                    #####pages (int): Another decimal integer

            Returns:
                    text (File): A text file
    '''
    if not pages:
        pagenums = set()
    else:
        pagenums = set(pages)
    output = io.StringIO()
    manager = PDFResourceManager()
    converter = TextConverter(manager, output, laparams=LAParams())
    interpreter = PDFPageInterpreter(manager, converter)
    infile = open(fname, 'rb')
    for page in PDFPage.get_pages(infile, pagenums):
        interpreter.process_page(page)
    infile.close()
    converter.close()
    text = output.getvalue()
    output.close
    return text 

#convert files docx to text:
def convertTodocx(doc_path):
    try:
        temp = docx2txt.process(doc_path)
        text = temp.replace('\t', '')
        return ''.join(text)
    except KeyError:
        return ' '

def convertTodoc(filepath, file):
    doc_file = filepath + file
    docx_file = filepath + file + 'x'
    if not os.path.exists(docx_file):
        print('antiword ' + doc_file + ' > ' + docx_file)
        os.system('antiword ' + doc_file + ' > ' + docx_file)
        with open(docx_file) as f:
            text = f.read()
            print(text)
        os.remove(docx_file) #docx_file was just to read, so deleting
    else:
        print('Info : file with same name of doc exists having docx extension, so we cant read it')
        text = ''
    return text

def find_index(content, text):
    start = content.find(text)
    end = len(text) + start
    return start, end

def extract_info(content, t):
    couples = t.split(';;;')
    info = []
    for couple in couples:
        try :
            text, label = couple.split(':::')
            start = content.find(text[:50]) 
            end = start+len(text) 
            pair = (start, end, label)
            info.append(pair)
        except : 
            pass
    return info

#Data annotation:
def convertion(df):
    train_data = []
    for _, row in df.iterrows():
        content = convertTopdf(PATH_PDF + '/' + row.file).lower()
        content = " ".join(content.split())
        entities = extract_info(content, row.text.lower())
        train_data.append((content, {"entities":entities}))
    print("conversion reussite")
    return train_data

train = pd.read_excel('./lib/train.xlsx', header=0)
Train = convertion(train)

# nlp.create_pipe works for built-ins that are registered with spaCy
if 'ner' not in nlp.pipe_names:
    ner = nlp.create_pipe('ner')
    nlp.add_pipe(ner, last=True)

# add labels
for _, annotations in Train:
    for ent in annotations.get('entities'):
        for label in LABELS:
            ner.add_label(label)
other_pipes = [pipe for pipe in nlp.pipe_names if pipe != 'ner']

# get names of other pipes to disable them during training
def train(Train, nlp):    
    l = []
    with nlp.disable_pipes(*other_pipes):  # only train NER
        optimizer = nlp.begin_training()
        los=501
        for itn in range(100):
            random.shuffle(Train)
            losses = {}
            if(los>500):
                for text, annotations in Train:
                    nlp.update(
                        [text],  # batch of texts
                        [annotations],  # batch of annotations
                        drop=0.01,  # dropout - make it harder to memorise data
                        sgd=optimizer,  # callable to update weights
                        losses=losses)
                
                los = int(losses.get('ner'))
                l.append([itn, losses.get('ner')])
                
            else:
                return l
    return l

def test(files):
    df=pd.DataFrame(columns=["MissionsCOMPETENCES"])
    i_files=0
    for f in files:
        c = ''
        i_files=i_files+1
        if 'docx' in f:
            c = convertTodocx(PATH_WORD + '/' + f).lower().replace('\n', '')
        elif 'pdf' in f:
            c = convertTopdf(PATH_PDF + '/' + f).lower().replace('\n', '')
        else:
            next
        doc2 = nlp(c)
        for ent in doc2.ents:
            if(ent.label_== "missions"):
                df.loc[i_files]=ent.text         
    return df 

TrainedModel = train(Train, nlp)

def getAllCompetences(Dic):
    allCompetences=[]
    for cle, valeur in Dic.items():
        for i in range(0,len(valeur)-1):
            allCompetences.append(valeur[i])
    return list(dict.fromkeys(allCompetences)) 

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def get_competences(file) : 
    outputFiles = test([file])
    output = outputFiles
    competencesCle = []
    l = []
    c = []
    for index, row in output.iterrows():
        ligne = row["MissionsCOMPETENCES"]
        #listeCompetence=[]
        competences = []
        tokens = nltk.word_tokenize(str(ligne))
        for cle, valeur in Dic.items():
            for i in range(0,len(valeur)-1):
                listeCompetence = []
                for j in range(0,len(tokens)-1):
                    #calculer la similarite: 
                    if(similar(tokens[j].lower(),valeur[i].lower())>0.66):
                        #listeCompetence.append(valeur[i])
                        competences.append(valeur[i])
        l.append(ligne)
        c.append(competences)
    competencesCle = dict(zip(l,c))
    liste = list(getAllCompetences(Dic))
    l = []
    lo = []
    onehotencoding=[]
    for cle,v in competencesCle.items():
            find = [0]*len(liste)
            for j in v:
                l.append(liste.index(j))
            for i in range(0,len(l)-1):
                find[l[i]] = 1 
            onehotencoding.append(find)
    gg = onehotencoding
    gg = np.array(onehotencoding)
    listeNew = gg.transpose( )
    d = dict.fromkeys(liste, 0)
    newdf = output.assign(**d)
    newdf[liste] = onehotencoding
    return newdf,competencesCle