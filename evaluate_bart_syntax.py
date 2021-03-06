# -*- coding: utf-8 -*-
"""Evaluate Bart syntax

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Ce8Cy6U7tsuhpRbH6uAoIEdczB6uhJ5e

# Syntactic analysis of BART.
This is the google colab notebook that goes along with the medium blog. You can use this repo to reproduce the results reported.

You will need the [LGD dataset](https://github.com/naveenjafer/bert-syntax/blob/master/lgd_dataset.tsv) to be uploaded to the file explorer on the left before starting.

Running this on a GPU runtime would take ~4 minutes.
"""
'''
! pip install torch
! pip install transformers
'''
import torch
from transformers import BartTokenizer, BartForConditionalGeneration

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = BartTokenizer.from_pretrained('bart-large')
model = BartForConditionalGeneration.from_pretrained('bart-large').to(device)
model.eval()

skipped = 0
missed = 0
words_hist = {}

def get_probs_for_words(inputList):
    global missed
    #print(tokenized_text)
    sentVectors = []
    targetWords = []

    for item in inputList:
        sent = item[0]
        w1 = item[1]
        w2 = item[2]
        pre,target,post = sent.split('***')

        if 'mask' in target.lower():
            target = '<mask>'
        else:
            target=tokenizer.tokenize(target)

        sentVectors.append(pre+target+post)
        targetWords.append([w1,w2])

    encoded_dict = tokenizer.batch_encode_plus(sentVectors, return_tensors='pt', pad_to_max_length=True)
    tokens_tensor = encoded_dict['input_ids']
    attention_masks = encoded_dict['attention_mask']

    with torch.no_grad():
        outputs = model(tokens_tensor.to(device), attention_masks.to(device))
        predictions = outputs[0]
        predictions = predictions.to(device)

    validSentsCount = 0
    correctRelative = 0
    correctAbsolute = 0
    outputArrayForLogging = []
    for index,item in enumerate(predictions):
        masked_index = (tokens_tensor[index] == tokenizer.mask_token_id).nonzero().item()

        probs = predictions[index, masked_index]
        word_id_1 = tokenizer.encode(targetWords[index][0])
        word_id_2 = tokenizer.encode(targetWords[index][1])
        prediction_w1 = probs[word_id_1][1:len(word_id_1)-1]
        prediction_w2 = probs[word_id_2][1:len(word_id_2)-1]

        values, predictionsT = probs.topk(10)
        predicted_token = tokenizer.decode(predictionsT).split()[0]

        if len(prediction_w1) > 1 or len(prediction_w2) > 1:
            missed = missed + 1
            outputArrayForLogging.append(None)
            continue
        else:
            validSentsCount = validSentsCount + 1

        if float(prediction_w1[0]) > float(prediction_w2[0]):
            correctRelative = correctRelative + 1
            outputArrayForLogging.append(True)
        else:
            outputArrayForLogging.append(False)

        if targetWords[index][0] == predicted_token:
            correctAbsolute = correctAbsolute + 1

    return([validSentsCount, correctRelative, correctAbsolute, outputArrayForLogging])

"""The driver program **eval_lgd** batches sentences into 128 sentences and calls **get_probs_for_words** for each of the batches to calculate the number of correct predictions of the masked LM."""

def eval_lgd():
    global missed
    missed = 0
    global words_hist
    truncate_at = 200
    count_correct_task = 0
    batch_size = 128
    count_correct_abs = 0
    counter = 0
    words_hist = {}
    counts_na = {}
    batchCounter = 0
    batchList = []
    f = open("lgd_dataset.tsv",encoding="utf8")
    for i,line in enumerate(f):

        batchCounter = batchCounter + 1
        print("Evaluating Sample: ", batchCounter)
        na,_,masked,good,bad = line.strip().split("\t")

        if good == bad:
          continue
        batchList.append([masked,good,bad,na,batchCounter])
        if batchCounter % batch_size == 0:
            #print("Missed is", missed)
            ps = get_probs_for_words(batchList)

            for index, item in enumerate(ps[3]):
                if item != None:
                  if batchList[index][1] not in words_hist:
                      words_hist[batchList[index][1]] = {
                      "count_correct" : 0,
                      "counter" : 0,
                      "sents" : []
                      }

                  if batchList[index][3] not in counts_na:
                      counts_na[batchList[index][3]] = {
                      "count_correct_task" : 0,
                      "counter" : 0
                      }
                  if item == True:
                      counts_na[batchList[index][3]]["count_correct_task"] = counts_na[batchList[index][3]]["count_correct_task"] + 1
                      words_hist[batchList[index][1]]["count_correct"] = words_hist[batchList[index][1]]["count_correct"] + 1
                  counts_na[batchList[index][3]]["counter"] = counts_na[batchList[index][3]]["counter"] + 1
                  words_hist[batchList[index][1]]["counter"] = words_hist[batchList[index][1]]["counter"] + 1
                  words_hist[batchList[index][1]]["sents"].append(batchList[index][4])

            batchList = []

    if len(batchList) > 0:
        ps = get_probs_for_words(batchList)

        for index, item in enumerate(ps[3]):
            if item != None:
              if batchList[index][1] not in words_hist:
                  words_hist[batchList[index][1]] = {
                  "count_correct" : 0,
                  "counter" : 0,
                  "sents " : []
                  }

              if batchList[index][3] not in counts_na:
                  counts_na[batchList[index][3]] = {
                  "count_correct_task" : 0,
                  "counter" : 0
                  }
              if item == True:
                  counts_na[batchList[index][3]]["count_correct_task"] = counts_na[batchList[index][3]]["count_correct_task"] + 1
                  words_hist[batchList[index][1]]["count_correct"] = words_hist[batchList[index][1]]["count_correct"] + 1
              counts_na[batchList[index][3]]["counter"] = counts_na[batchList[index][3]]["counter"] + 1
              words_hist[batchList[index][1]]["counter"] = words_hist[batchList[index][1]]["counter"] + 1
              words_hist[batchList[index][1]]["sents"].append(batchList[index][4])

    for item in counts_na:
        print("Category: ", item)
        print("\tAccuracy: ", counts_na[item]["count_correct_task"] /  counts_na[item]["counter"])
        print("\tTotal Samples: ", counts_na[item]["counter"])
        print("\n")


    '''print("Word summary")
    print("Total number of verbs: ", len(words_hist))

    for word in words_hist:
        print("Word: ", word)
        print("\tAccuracy: ", words_hist[word]["count_correct"] / words_hist[word]["counter"])
        print("\tTotal Samples: ", words_hist[word]["counter"])'''

eval_lgd()

print("Skipping ", missed, " samples since the verb is decomposed.")

"""# Analysis of verbs with low performance.
We display the words with low accuracy (Below 0.90) and also the sentences numbers where the word was present. One can explore them further to see the kind of mistakes the model makes.
"""

def analysisOfVerbSuccessRates(accuracyBelow):
  for word in {k: v for k, v in sorted(words_hist.items(), key = lambda item: item[1]["count_correct"]/item[1]["counter"])}:
    if words_hist[word]["counter"] > 10 and (words_hist[word]["count_correct"] / words_hist[word]["counter"] < accuracyBelow):
      print("Word: ", word)
      print("\tAccuracy: ", round(words_hist[word]["count_correct"] / words_hist[word]["counter"],2))
      print("\tTotal Samples: ", words_hist[word]["counter"])
      print("\tSentence Numbers: ", words_hist[word]["sents"])

analysisOfVerbSuccessRates(0.9)
