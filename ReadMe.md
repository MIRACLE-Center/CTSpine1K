step 1: /home/yangdeng/nnUnet/Verse20/train/ 目录下，image 和label 的命名后缀分别是：.nii.gz 和 _seg.nii.gz

step 2: python Task056_VerSe2019.py to generate /home/usename/nnUnet/nnUNet_raw/nnUNet_raw_data/

step 3: nnUNet_plan_and_preprocess -t 056 --verify_dataset_integrity

step 4: nnUNet_train 3d_fullres nnUNetTrainerV2 Task056_VerSe all

step 5: nnUNet_predict -i input -o output -t 056 -m 3d_fullres -f all

step 6: nnUNet_evaluate_folder -ref FOLDER_WITH_GT -pred FOLDER_WITH_PREDICTIONS -l  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25  
the name should be the same and the result will be saved in FOLDER_WITH_PREDICTIONS

note：load pretrained_weights for fine-tuning: https://github.com/MrGiovanni/ModelsGenesis/tree/master/competition

 nnUNet_train 3d_fullres nnUNetTrainerV2 Task056_VerSe all -w model

ACK:
https://github.com/MIC-DKFZ/nnUNet
https://github.com/MrGiovanni/ModelsGenesis/tree/master/competition