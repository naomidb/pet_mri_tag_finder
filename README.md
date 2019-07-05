Running this program is very simple.
`python pet_mri_fill_in.py <path_to_folder>`

The program will create two csv files-- one for PET images and one for MRI images. The folder can contain both mixed together and they will be seperated via the Modality tag.

If you are building off a previously created csv file for either PET or MRI, you can use the -p and -m flags.

`python pet_mri_fill_in.py <path_to_folder> -p <path_to_pet_file> -m <path_to_mri_file>`

Be aware that files are named after the day. If you run the program twice on the same day without using the -p or -m flags, you will overwrite your file.
