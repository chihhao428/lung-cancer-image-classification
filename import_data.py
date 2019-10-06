#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct  4 23:04:35 2019

@author: hsunwei
"""

import glob
import os
import numpy as np
import pandas as pd
import pydicom


INPUT_FOLDER = '../data/SPIE-AAPM/SPIE-AAPM Lung CT Challenge/'
patients = os.listdir(INPUT_FOLDER)
patients.sort()


# Load the slices in given folder path
def load_scan(path):
    path = INPUT_FOLDER + path
    
    slices = [pydicom.dcmread(s) for s in glob.glob(path + '/*/*/*.dcm')]
#     slices = [pydicom.read_file(s) for s in glob.glob(path + '/*/*/*.dcm')]
    print(slices)
    slices.sort(key = lambda x: float(x.ImagePositionPatient[2]))
    try:
        slice_thickness = np.abs(slices[0].ImagePositionPatient[2] - slices[1].ImagePositionPatient[2])
    except:
        slice_thickness = np.abs(slices[0].SliceLocation - slices[1].SliceLocation)
        
    for s in slices:
        s.SliceThickness = slice_thickness
        
    return slices

def get_pixels_hu(slices):
    image = np.stack([s.pixel_array for s in slices])
    # Convert to int16 (from sometimes int16), 
    # should be possible as values should always be low enough (<32k)
    image = image.astype(np.int16)

    # Set outside-of-scan pixels to 0
    # The intercept is usually -1024, so air is approximately 0
    image[image == -2000] = 0
    
    # Convert to Hounsfield units (HU)
    for slice_number in range(len(slices)):
        
        intercept = slices[slice_number].RescaleIntercept
        slope = slices[slice_number].RescaleSlope
        
        if slope != 1:
            image[slice_number] = slope * image[slice_number].astype(np.float64)
            image[slice_number] = image[slice_number].astype(np.int16)
            
        image[slice_number] += np.int16(intercept)
    
    return np.array(image, dtype=np.int16)

# Load the number of slices in given folder path
def load_scan_count(path):
    slices = [s for s in glob.glob(INPUT_FOLDER + path + '/*/*/*.dcm')]        
    return len(slices)

# Load the specified slice in given folder path
def load_scan_num(num, path):
    # print(glob.glob(INPUT_FOLDER + path + '/*/*/*' + str(num) + '.dcm'))
    slices = pydicom.dcmread(glob.glob(INPUT_FOLDER + path + '/*/*/*' + str(num) + '.dcm')[0])
    return slices.pixel_array

# Load pixels for dataframe
def load_scan_df(df):
    return load_scan_num(df['z'], df['path'])

#%%
# Load label data

# Load all 
df_train = pd.read_excel(INPUT_FOLDER + '../CalibrationSet_NoduleData.xlsx', dtype={'Nodule Center x,y Position*': str})
df_train.dropna(subset=['Diagnosis'], inplace=True)
df_train['Diagnosis'] = np.where(df_train['Diagnosis'].str.contains('benign'), 0, 1)
df_train['Diagnosis'] = df_train['Diagnosis'].astype('category')

df_train['x'] = df_train['Nodule Center x,y Position*'].apply(lambda x: x[:-3])
df_train['y'] = df_train['Nodule Center x,y Position*'].apply(lambda x: x[-3:])
df_train['z'] = df_train['Nodule Center Image'].astype('int')
df_train.drop(columns=['Nodule Center x,y Position*'], inplace=True)
df_train.drop(columns=['Nodule Center Image'], inplace=True)

df_train.rename(columns={'Scan Number':'patient_id',
                          'Diagnosis':'diagnosis'}, 
                 inplace=True)
df_train.patient_id = df_train.patient_id.str.lower()
df_train.head(3)


# In[5]:


df_test = pd.read_excel(INPUT_FOLDER + '../TestSet_NoduleData_PublicRelease_wTruth.xlsx', dtype={'Nodule Center x,y Position*': str})
df_test.dropna(subset=['Final Diagnosis'], inplace=True)
df_test['Final Diagnosis'] = np.where(df_test['Final Diagnosis'].str.contains('benign', False), 0, 1)
df_test['Final Diagnosis'] = df_test['Final Diagnosis'].astype('category')

df_test['x'] = df_test['Nodule Center x,y Position*'].apply(lambda x: x[:-3])
df_test['x'] = df_test['x'].str.replace(",", "")
df_test['y'] = df_test['Nodule Center x,y Position*'].apply(lambda x: x[-3:])
df_test['z'] = df_test['Nodule Center Image'].astype('int')
df_test.drop(columns=['Nodule Center x,y Position*'], inplace=True)
df_test.drop(columns=['Nodule Center Image'], inplace=True)

df_test.rename(columns={'Scan Number':'patient_id',
                        'Nodule Number':'nodule_number',
                        'Final Diagnosis':'diagnosis'}, 
                 inplace=True)
df_test['nodule_number'] = df_test['nodule_number'].astype('int')
df_test.patient_id = df_test.patient_id.str.lower()
df_test.head(3)


#%%
# Data

# Append df_train and df_test
table = df_train.append(df_test)
table['nodule_number'].fillna('1', inplace=True)
table = table[['patient_id', 'nodule_number', 'diagnosis', 'x', 'y', 'z']]
table.head(3)

# Convert patients to df and append data
data = pd.DataFrame(patients, columns=['path'])
data['patient_id'] = data['path'].str.lower()
data = pd.merge(data, table, on='patient_id')

# Load pixel_array for each row
data['pixel'] = data.apply(load_scan_df, axis=1)
# data['pixel_flatten'] = data.pixel.values.reshape(-1)
# data['pixel_flatten'] = data.pixel.apply(np.ndarray.flatten) #.apply(np.ndarray.tolist)
# data['pixel_flatten'] = data.pixel_flatten.apply(np.ndarray.tolist)
data.head(3)