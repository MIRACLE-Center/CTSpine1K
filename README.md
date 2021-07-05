# Update 7/5/2021
Note that for VerSe dataset partially visible vertebrae at the top or bottom of the scan (or both) were not annotated, while CTSpine1K annotated them, which caused the situation that in our previous-version paper the reported dice value on VerSe dataset is much lower than on CTSpine1K dataset (0.619 VS 0.840). Therefore, we annotated all visible vertebrea (see figure below) and recalculated the metrics(0.766 VS 0.840). 

We have updated our paper on [arxiv](https://arxiv.org/abs/2105.14711) and uploaded the completed annotations for VerSe dataset to Google drive [Google drive](https://drive.google.com/drive/folders/12kFn2H0xsACqGN3S9lInqizVlbpjNwdj?usp=sharing) and [Baiduyun](https://pan.baidu.com/s/10oF_QMKt1RbEK4NyEasEXQ) (password：send email to dengy066@gmail.com).
![label](https://user-images.githubusercontent.com/54644867/124413086-8a41ff00-dd82-11eb-8a18-84279b85788b.PNG)

Besides, we updated a more specific biconcave fracture case on Figure 1(F).

# Update 6/11/2021
We upload the Path.csv to clarify the CT positions we used for COLONOG dataset and HNSCC-3DCT-RT dataset, and delete the dicom2nii.py file. We also upload the original CT images to [Baiduyun](https://pan.baidu.com/s/10oF_QMKt1RbEK4NyEasEXQ) (password：send email to dengy066@gmail.com)

# Introduction for the CTSpine1K dataset
To advance the research in spinal image analysis, we hereby present a large-scale and comprehensive dataset: CTSpine1K.
To build a comprehensive spine dataset that replicates practical appearance variations, we curate CTSpine1K from the following four open sources, totalling 1,005 CT volumes (over 500,000 labeled slices and over 11,000 vertebrae) of diverse appearance variations. 

*[COLONOG](https://wiki.cancerimagingarchive.net/display/Public/CT+COLONOGRAPHY). This sub-dataset comes from the CT COLONOGRAPHY dataset related to a CT colonography trial12. We randomly select one of the two positions (we open the code for selecting them, dicom2nii.py), which have similar information, of each patient for our dataset . There are 825 CT scans and are in Digital Imaging and Communication in Medicine (DICOM) format.

*[HNSCC-3DCT-RT](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=39879146). This sub-dataset contains three dimensional (3D) high-resolution fan-beam CT scans collected during
pre-treatment, mid-treatment, and post-treatment using a Siemens 16-slice CT scanner with the standard clinical protocol for head-and-neck squamous cell carcinoma (HNSCC) patients13. These images are in DICOM format.

*[MSD T10](https://drive.google.com/file/d/1jyVGUGyxKBXV6_9ivuZapQS8eUJXCIpu/view?usp=sharing). This sub-dataset comes from the 10th Medical Segmentation Decathlon14. To attain more slices containing the
spine, we select the task03_liver dataset consisting of 201 cases. These images are in Neuroimaging Informatics Technology
Initiative (NIfTI) format (https://nifti.nimh.nih.gov/nifti-1).

*[COVID-19](https://wiki.cancerimagingarchive.net/display/Public/CT+Images+in+COVID-19). This sub-dataset consists of non-enhanced chest CTs from 632 patients with COVID-19 infections. The images were acquired at the point of care in an outbreak setting from patients with Reverse Transcription Polymerase Chain Reaction(RT-PCR) confirmation for the presence of SARS-CoV-215. We pick 40 scans with the images stored in NIfTI format.

We reformat all DICOM images to NIfTI to simplify data processing and de-identify images, meeting the institutional
review board (IRB) policies of contributing sites. More details for those sub-datasets could be found in12–15. All existing sub-datasets are under Creative Commons license CC-BY-NC-SA and we will keep the license unchanged. It should be noted that for sub-dataset task03_liver and sub-dataset COVID-19, we only choose a part of cases from them, and in all these data sources, we exclude those cases of very low quality. The overview of our dataset and the thorough comparison with the [VerSe Challenge](https://verse2020.grand-challenge.org/) dataset (*We only chose those samples which are not cropped*) can be seen in Table 1.

![spine1K](https://user-images.githubusercontent.com/54644867/118909650-e88f5b80-b955-11eb-8a60-e1831a495c99.PNG)
![situation](https://user-images.githubusercontent.com/54644867/124413701-bdd15900-dd83-11eb-9b02-b2270aec077b.PNG)



For more information about CTSpine1K dataset, please read the following paper. Please also cite this [paper](https://arxiv.org/abs/2105.14711) if you are using CTSpine1K dataset for your research.

```
Yang Deng, Ce Wang, Yuan Hui, et al. CtSpine1k: A large-scale dataset for spinal vertebrae segmentation in computed tomography. arXiv preprint arXiv:2105.14711 (2021). 
```

# Downloading the CTSpine1K Dataset
The original images could be downloaded from correspongding URL above. 

The segmentation masks and the pre-trained model are on [Google drive](https://drive.google.com/drive/folders/12kFn2H0xsACqGN3S9lInqizVlbpjNwdj?usp=sharing) or [Baiduyun](https://pan.baidu.com/s/10oF_QMKt1RbEK4NyEasEXQ) (password：send email to dengy066@gmail.com) 


# Annotation pipeline with nnUnet
Follow https://github.com/MIC-DKFZ/nnUNet/commit/058b695d61d34dda7f79cd36ab950a5d3e031653 to set and use nnUnet. The specific usage we here could be seen in ReadMe.md file.  Our annotation pipeline is presented in figure 2 below.
![annotataion](https://user-images.githubusercontent.com/54644867/118924193-5431f280-b96f-11eb-851a-e58bdf152069.PNG)

# Benchmarking results
The benchmarking results are shown in Table 2.
![table](https://user-images.githubusercontent.com/54644867/124412945-346d5700-dd82-11eb-8be5-e81c36a2fae1.PNG)

# Acknowledgement
Thank Febian's nnUnet and we appreciate the open-source sub-datasets we used. 

Thank Jianji Wang and Guoxin Fan(MD) for their help in Fig.1(F)
 
Please feel free to email dengy066@gmail.com if you have any question. 

