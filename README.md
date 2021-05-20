# CTspine1K
A Large-Scale Dataset for Spinal Vertebrae Segmentation in Computed Tomography

To advance the research in spinal image analysis, we hereby present a large-scale and comprehensive dataset: CTSpine1K.
We collect and annotate a large-scale spinal vertebrae CT dataset from multiple domains and different manufacturers, totalling 1,005 CT volumes (over 500,000 labeled slices and over 11,000 vertebrae) of diverse appearance variations. 

To build a comprehensive spine dataset that replicates practical appearance variations, we curate a large-scale CT dataset of spinal vertebrae from the following four open sources.

*COLONOG. This sub-dataset comes from the CT COLONOGRAPHY dataset related to a CT colonography trial12. We randomly select one of the two positions (we will open the code for selecting them), which have similar information, of each patient for our dataset . There are 825 CT scans and are in Digital Imaging and Communication in Medicine (DICOM) format.

*HNSCC-3DCT-RT. This sub-dataset contains three dimensional (3D) high-resolution fan-beam CT scans collected during
pre-treatment, mid-treatment, and post-treatment using a Siemens 16-slice CT scanner with the standard clinical protocol for head-and-neck squamous cell carcinoma (HNSCC) patients13. These images are in DICOM format.

*MSD T10. This sub-dataset comes from the 10th Medical Segmentation Decathlon14. To attain more slices containing the
spine, we select the task03_liver dataset consisting of 201 cases. These images are in Neuroimaging Informatics Technology
Initiative (NIfTI) format (https://nifti.nimh.nih.gov/nifti-1).

*COVID-19. This sub-dataset consists of non-enhanced chest CTs from 632 patients with COVID-19 infections. The images were acquired at the point of care in an outbreak setting from patients with Reverse Transcription Polymerase Chain Reaction(RT-PCR) confirmation for the presence of SARS-CoV-215. We pick 40 scans with the images stored in NIfTI format.

We reformat all DICOM images to NIfTI to simplify data processing and de-identify images, meeting the institutional
review board (IRB) policies of contributing sites. More details for those sub-datasets could be found in12–15. All existing sub-datasets are under Creative Commons license CC-BY-NC-SA and we will keep the license unchanged. It should be noted that for sub-dataset task03_liver and sub-dataset COVID-19, we only choose a part of cases from them, and in all these data sources, we exclude those cases of very low quality. The overview of our dataset and the thorough comparison with the VerSe Challenge dataset can be seen in Table 1.

![spine1K](https://user-images.githubusercontent.com/54644867/118909650-e88f5b80-b955-11eb-8a60-e1831a495c99.PNG)
![fig1](https://user-images.githubusercontent.com/54644867/118909767-0fe62880-b956-11eb-8def-44001c78741b.PNG)

For more information about CTSpine1K dataset, please read the following paper. Please also cite this paper if you are using CTSpine1K dataset for your research!