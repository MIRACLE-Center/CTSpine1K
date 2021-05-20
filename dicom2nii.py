# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 11:42:14 2020

@author: 91952


import SimpleITK as sitk
import os

def readdcm(filepath):
    series_id = sitk.ImageSeriesReader.GetGDCMSeriesIDs(filepath)
    print(series_id)
    series_file_names = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(filepath, series_id[0])
    series_reader = sitk.ImageSeriesReader() 
    series_reader.SetFileNames(series_file_names)  
    images = series_reader.Execute()
    return images
    
    
path1 = '/home1/username/COLON/COLONOG/CT COLONOGRAPHY/'
path2 = '/home1/username/spine_segmentation/colon/'
if not os.path.exists(path2):
    os.makedirs(path2)

for volumeID in sorted(os.listdir(path1)):
    print(volumeID)
    print ('Processing File ' + volumeID)
    filename1 =  volumeID
    directory1 = os.path.join(path1, filename1)
    filename2 = volumeID + '.nii.gz'
    for path_, _, file_ in os.walk(directory1):
        L = len(sorted(file_)[1:])
        if L > 10:
            print ('  ' + str(L) + ' slices along the axial view.')
            print(directory1)
            #file1 = os.path.abspath(os.path.join(path_, file_))
            print(os.path.abspath(path_))
            dcm_images = readdcm(os.path.abspath(path_))
            sitk.WriteImage(dcm_images, os.path.join(path2,volumeID+".nii.gz"))
print ('File ' + volumeID + ' is saved in ' + path2 + ' .')