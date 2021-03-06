#!/usr/bin/python

import data
import ngrams
import validate
import classifier
import os
from numpy import *
from operator import itemgetter
from Indexes import Indexes

POS_DIR="pos"
POS_POSITION_DIR="pos_position"
POS_PARTOFSPEECH_DIR="pos_tagged"
POS_ADJ_DIR="pos_adj"
POS_VERB_DIR="pos_verb"

NEG_DIR="neg"
NEG_POSITION_DIR="neg_position"
NEG_PARTOFSPEECH_DIR="neg_tagged"
NEG_ADJ_DIR="neg_adj"
NEG_VERB_DIR="neg_verb"

YELP_DIR = "yelp/default"

class TestConfiguration:
    def __init__(self, clsf, n, ind, pos_dir, neg_dir, test_set=None,
                 binary=False, limit=None, idf=False, negation = True):
        self.count = 0
        self.n = n
        self.index = ind
        self.binary = binary
        self.limit = limit if limit else [0 for i in n]
        self.clsf = clsf
        self.idf = idf
        self.test_set = test_set
        self.pos_dir = pos_dir
        self.neg_dir = neg_dir
        self.negation = negation

        # filenames needed for this test configuration used
        pos_files = os.listdir(pos_dir)
        self.pos_train_data = [open("%s/%s" % (pos_dir, pos_files[i])).read() \
                                   for i in self.index.get_pos_train_ind()]
        self.pos_test_data = [open("%s/%s" % (pos_dir, pos_files[i])).read() \
                                  for i in self.index.get_pos_test_ind()]

        neg_files = os.listdir(neg_dir)
        self.neg_train_data = [open("%s/%s" % (neg_dir, neg_files[i])).read() \
                                   for i in self.index.get_neg_train_ind()]
        self.neg_test_data = [open("%s/%s" % (neg_dir, neg_files[i])).read() \
                                  for i in self.index.get_neg_test_ind()]
        self.features = {}
    def set_index(self, ind):
        self.index = ind
        pos_dir = self.pos_dir
        neg_dir = self.neg_dir

        pos_files = os.listdir(pos_dir)
        self.pos_train_data = [open("%s/%s" % (pos_dir, pos_files[i])).read() \
                                   for i in self.index.get_pos_train_ind()]
        self.pos_test_data = [open("%s/%s" % (pos_dir, pos_files[i])).read() \
                                  for i in self.index.get_pos_test_ind()]

        neg_files = os.listdir(neg_dir)
        self.neg_train_data = [open("%s/%s" % (neg_dir, neg_files[i])).read() \
                                   for i in self.index.get_neg_train_ind()]
        self.neg_test_data = [open("%s/%s" % (neg_dir, neg_files[i])).read() \
                                  for i in self.index.get_neg_test_ind()]
        self.features = {}

    def train(self):
        pos_train = [{} for f in self.pos_train_data]
        neg_train = [{} for f in self.neg_train_data]
        
        # Reading files
        for (j,lim) in zip(self.n,self.limit):
            all_grams = [ngrams.ngrams(j, f, self.negation) for f in self.pos_train_data]
            for i in range(len(self.pos_train_data)):
                pos_train[i].update(all_grams[i])
            featureslist = all_grams

            all_grams = [ngrams.ngrams(j, f, self.negation) for f in self.neg_train_data]
            for i in range(len(self.neg_train_data)):
                neg_train[i].update(all_grams[i])
            featureslist.extend(all_grams)

            # Collapsing, limiting ngrams
            self.features.update(ngrams.top_ngrams(ngrams.collapse_ngrams(
                        featureslist),lim))

        # Creating Index
        self.classifier = self.clsf(restrictFeatures = self.features)
        print "# features: %s" % self.classifier.nfeatures
        
        if self.idf:
            print "Using TF-IDF"
            idf = ngrams.ngrams_to_idf(pos_train + neg_train)
            for i in range(len(pos_train)):
                for j in pos_train[i]:
                    pos_train[i][j] = pos_train[i][j] * idf[j]
            for i in range(len(neg_train)):
                for j in neg_train[i]:
                    neg_train[i][j] = neg_train[i][j] * idf[j]
                            
        # Making classifier
        for i in pos_train:
            self.count += 1
            self.classifier.addFeatureVector(i, 1, binary=self.binary)
        for i in neg_train:
            self.classifier.addFeatureVector(i, -1, binary=self.binary)
        self.classifier.compile()

    def test(self):
        if self.test_set:
            for s in range(1,6):
                self.test_dir = select_extradata(self.test_set,s)
                print "Testing with %s" % self.test_dir
                test_files = os.listdir(self.test_dir)
                ntest = len(test_files)
                tests = [{} for i in range(ntest)]
                for i in range(ntest):
                    for j in self.n:
                        tests[i].update(ngrams.ngrams(j, open("%s/%s" % (
                            self.test_dir,test_files[i])).read(), self.negation))
                results = [self.classifier.classify(i,binary=self.binary) for i in tests]
                correct = len([i for i in results if int(i) == 1])
                print "%s Stars, Positive: %s of %s, %s accuracy" % (s,correct,len(tests),
                        (float(correct)/len(tests)))
            return (0,0) # return dummy values when testing on external data

        pos_tests = [{} for f in self.pos_test_data]
        neg_tests = [{} for f in self.neg_test_data]

        # Testset --> Feature Vectors
        for j in self.n:
            for i in range(len(self.pos_test_data)):
                pos_tests[i].update(ngrams.ngrams(j, self.pos_test_data[i], self.negation))
            for i in range(len(self.neg_test_data)):
                neg_tests[i].update(ngrams.ngrams(j, self.neg_test_data[i], self.negation))

        # Testing
        pos_results = [self.classifier.classify(i,binary=self.binary) for i in pos_tests]
        pos_correct = len([i for i in pos_results if int(i) == 1])
        print "Positive: %s of %s, %s accuracy" % (pos_correct,len(pos_tests),
                (float(pos_correct)/len(pos_tests)))
        neg_results = [self.classifier.classify(i,binary=self.binary) for i in neg_tests]
        neg_correct = len([i for i in neg_results if int(i) == -1])
        print "Negative: %s of %s, %s accuracy" % (neg_correct,len(neg_tests),
                (float(neg_correct)/len(neg_tests)))
        return (float(pos_correct)/len(pos_tests), float(neg_correct)/len(neg_tests))

class MajorityVotingTester():
    def __init__(self, negation):
        self.negation = negation
        self.testers = []
    def addClassifier(self, c):
        self.testers.append(c)
    def train(self):
        [x.train() for x in self.testers]
    def set_index(self, ind):
        [x.set_index(ind) for x in self.testers]
    def crossValidate(self, iterations, mode='k', train_size=500):
        ind = Indexes(mode=mode, iterations=iterations, train_size=train_size)
        pos_correct = 0
        neg_correct = 0
        for k in range(iterations):
            ind.next()
            self.set_index(ind)
            self.train()
            (pos, neg) = self.test()
            pos_correct += pos
            neg_correct += neg
        print "Results:"
        print "Positive:", round((pos_correct/iterations)*100), "%"
        print "Negative:", round((neg_correct/iterations)*100), "%"
        print "Total:", round((neg_correct + pos_correct)/(2*iterations)*100), "%"

            
    def test(self):
        pos_test_votes = False
        neg_test_votes = False
        for t in self.testers:
            pos_tests = [{} for f in t.pos_test_data]
            neg_tests = [{} for f in t.neg_test_data]
            for j in t.n:
                for i in range(len(t.pos_test_data)):
                    pos_tests[i].update(ngrams.ngrams(j, t.pos_test_data[i], self.negation))
                for i in range(len(t.neg_test_data)):
                    neg_tests[i].update(ngrams.ngrams(j, t.neg_test_data[i], self.negation))
            pos_results = [t.classifier.classify(i) for i in pos_tests]
            neg_results = [t.classifier.classify(i) for i in neg_tests]
            if not pos_test_votes:
                pos_test_votes = pos_results
            else:
                for i in range(len(pos_test_votes)):
                    pos_test_votes[i] += pos_results[i]
            if not neg_test_votes:
                neg_test_votes = neg_results
            else:
                for i in range(len(neg_test_votes)):
                    neg_test_votes[i] += neg_results[i]
        pos_correct = 0
        neg_correct = 0
        for i in pos_test_votes:
            if i > 0:
                pos_correct += 1
        for i in neg_test_votes:
            if i < 0:
                neg_correct += 1

        print "Positive: %s of %s, %s accuracy" % (pos_correct,len(pos_test_votes),
                (float(pos_correct)/len(pos_test_votes)))

        print "Negative: %s of %s, %s accuracy" % (neg_correct,len(neg_test_votes),
                (float(neg_correct)/len(neg_test_votes)))
        return (float(pos_correct)/len(pos_test_votes), float(neg_correct)/len(neg_test_votes))

def select_dataset(dataset):
    return {'default':(POS_DIR, NEG_DIR), #untagged
            'partofspeech':(POS_PARTOFSPEECH_DIR, NEG_PARTOFSPEECH_DIR), #part of speech tagged
            'position':(POS_POSITION_DIR, NEG_POSITION_DIR), #position tagged
            'adjectives':(POS_ADJ_DIR, NEG_ADJ_DIR), #adjectives tagged
            'verbs':(POS_VERB_DIR, NEG_VERB_DIR), #verbs tagged
            }[dataset]

def select_extradata(dataset,stars):
    return {'default':("%s/%sstar_limited" % (YELP_DIR,stars)), #yelp untagged
            'partofspeech':("%s/%sstar_limited_tagged" % (YELP_DIR,stars)), #yelp part of speech tagged
            'position':("%s/%sstar_limited_position" % (YELP_DIR,stars)), #yelp position tagged
            'adjectives':("%s/%sstar_limited_adj" % (YELP_DIR,stars)), #yelp adjectives only
            'verbs':("%s/%sstar_limited_verb" % (YELP_DIR,stars)), #yelp verbs only
            }[dataset]

def test(classif, n=1, train_size=500, mode='k', iterations=1, dataset='',
         extra_dataset=None, limit=None, binary=False, idf=False, negation=True):
    (pos_dir, neg_dir) = select_dataset(dataset)
    if extra_dataset:
        mode='d'
        iterations=1
        train_size = 1000
        test_set = dataset
    else:
        test_set = None

    print "TEST CONFIGURATION"
    print "dataset: %(dataset)s, stars: %(extra_dataset)s \nn: %(n)s, limit: %(limit)s, binary: %(binary)s, \nmode: %(mode)s, iterations: %(iterations)s, idf: %(idf)s" % {'n':n,
            'train_size':train_size,
            'mode':mode,
            'iterations':iterations,
            'dataset':dataset,
            'extra_dataset':extra_dataset,
            'limit':limit,
            'binary':binary,
            'idf':idf}

    ind = Indexes(mode=mode,iterations=iterations,train_size=train_size)
    (pos_correct, neg_correct) = (0,0)
    for k in range(iterations):
        ind.next()
        m = TestConfiguration(classif, n, ind, pos_dir, neg_dir, idf=idf,
                              test_set=test_set, binary=binary, limit=limit, negation=negation)
        m.train()
        (pos, neg) = m.test()
        pos_correct += pos
        neg_correct += neg
    print "Results:"
    print "Positive:", round((pos_correct/iterations)*100), "%"
    print "Negative:", round((neg_correct/iterations)*100), "%"
    print "Total:", round((neg_correct + pos_correct)/(2*iterations)*100), "%"

if __name__ == "__main__":


    n = [1]
    dataset = 'default'
    limit = None

    binary = True
    idf = False
    negation = True

    train_size = 800
    mode = 'k'
    iterations = 3
    extra_dataset=None
    

#    print "Bayes:"
#    test(classifier.BayesClassifier,n=n,train_size=train_size,mode=mode,iterations=iterations,
#            dataset=dataset,extra_dataset=extra_dataset,limit=limit,binary=binary, idf=idf, negation = negation)
    print "MaxEnt:"
#    test(classifier.MaximumEntropyClassifier,n=n,train_size=train_size,mode=mode,iterations=iterations, dataset=dataset,extra_dataset=extra_dataset,limit=limit,binary=binary, idf=idf, negation=negation)
 #   print "SVM:"
#    test(classifier.LinearSVMClassifier,n=n,train_size=train_size,mode=mode,iterations=iterations, dataset=dataset,extra_dataset=extra_dataset,limit=limit,binary=binary, idf=idf, negation=negation)

    mvc = MajorityVotingTester(negation)
    ind = Indexes(mode='k',iterations=3,train_size=800)
    ind.next()
    print ind
    (pos_dir, neg_dir) = select_dataset(dataset)
    m1 = TestConfiguration(classifier.BayesClassifier, n=n, ind=ind, pos_dir=pos_dir, neg_dir=neg_dir, binary=binary, limit=limit, idf=idf)
    mvc.addClassifier(m1)

    (pos_dir, neg_dir) = select_dataset(dataset)
    m2 = TestConfiguration(classifier.MaximumEntropyClassifier, n=n, ind=ind, pos_dir=pos_dir, neg_dir=neg_dir, binary=binary, limit=limit, idf=idf)

    mvc.addClassifier(m2)


    (pos_dir, neg_dir) = select_dataset(dataset)
    m3 = TestConfiguration(classifier.LinearSVMClassifier, n=n, ind=ind, pos_dir=pos_dir, neg_dir=neg_dir, binary=binary, limit=limit, idf=idf)
    mvc.addClassifier(m3)

    
    mvc.train()
    mvc.crossValidate(3)
    exit()




# with train_size = 800, no shuffling, bayes classifier
# [ns]      dataset         [limits]        binary  --> +results    -results
# [2]       position        [114370]        0       --> 0.96        0.56
# [1,2]     default         [0,0]           0       --> 0.96        0.56 
# [1,2]     default         [16165,16165]   0       --> 0.94        0.71
# [1]       default         [16165]         0       --> 0.92        0.69
# [2]       default         [16165]         0       --> 0.93        0.69
# [1]       default         [2633]          0       --> 0.94        0.61
# [1]       default         [2633]          1       --> 0.76        0.86
# [1]       default         [16165]         1       --> 0.77        0.84
# [2]       default         [16165]         1       --> 0.86        0.77
# [1,2]     default         [16165,16165]   1       --> 0.89        0.81
# [1,2]     partofspeech    [16165,16165]   1       --> 0.65        0.91
# [1]       partofspeech    [16165,16165]   1       --> 0.67        0.91
# [1]       adjectives      [2633]          1       --> 0.92        0.70
# [1]       adjectives      [2633]          0       --> 0.97        0.54# [1]       default         [40183]         1       --> 0.83        0.79
