step 1: python Task056_VerSe2019.py to generate /home/username/nnUnet/nnUNet_raw/nnUNet_raw_data/

step 2: nnUNet_plan_and_preprocess -t 056 --verify_dataset_integrity

step 3: nnUNet_train 3d_fullres nnUNetTrainerV2 Task056_VerSe all

step 4: nnUNet_predict -i input -o output -t 056 -m 3d_fullres -f all

step 5: nnUNet_evaluate_folder -ref FOLDER_WITH_GT -pred FOLDER_WITH_PREDICTIONS -l  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25  
the name should be the same and the result will be saved in FOLDER_WITH_PREDICTIONS

note：load pretrained_weights for fine-tuning: https://github.com/MrGiovanni/ModelsGenesis/tree/master/competition
nnUNet_train 3d_fullres nnUNetTrainerV2 Task056_VerSe all -w pre-trained model

ACK:
https://github.com/MIC-DKFZ/nnUNet
https://github.com/MrGiovanni/ModelsGenesis/tree/master/competition
