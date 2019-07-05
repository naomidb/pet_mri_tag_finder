docstr = """
Usage:
    pet_mri_fill_in.py (-h | --help)
    pet_mri_fill_in.py <dicom_path> [-p <pet_file>] [-m <mri_file>]

Options:
  -p <file>, --pet <file>          Update from pre-existing pet file
  -m <file>, --mri <file>          Update from pre-existing mri file

"""

import csv
import datetime
import logging
import os
import platform
import sys

import pydicom
from docopt import docopt

DICOM_PATH = '<dicom_path>'
PET_FILE = '--pet'
MRI_FILE = '--mri'


def mount_iso(iso_path, mount_location):
    if not os.path.exists(mount_location):
        os.mkdir(mount_location)
    mount_point = mount_location + "/ISOImage"
    iso_path = iso_path.replace(' ', '\\ ')
    if platform.system() == 'Darwin':
        mount_command = "hdiutil mount -mountpoint {} {}".format(mount_point, iso_path) 
        os.system(mount_command)
    elif platform.system() == 'Linux':
        mount_command = "sudo mount -o loop {} {}".format(iso_path, mount_point)
        os.system(mount_command)
    else:
        os.rmdir(mount_location)
        exit("Error: This program must be run on MacOS or Linux")

    return mount_point


def unmount_iso(mount_location):
    if platform.system() == 'Darwin':
        os.system("hdiutil unmount {}/ISOImage".format(mount_location))
    elif platform.system() == 'Linux':
        os.system("sudo umount {}/ISOImage".format(mount_location))
    os.rmdir(mount_location)


def walk(parent_file, pet_values, mri_values):
    mount_location = "mount"
    pet_results = {}
    mri_results = {}
    if os.path.isfile(parent_file):
        logging.info("Working On: " + parent_file)
        try:
            if parent_file.endswith(".iso"):
                top_dir = mount_iso(parent_file, mount_location)
                walk(top_dir, pet_values, mri_values)
                unmount_iso(mount_location)
            else:
                result, scan_type = read_dicom(parent_file)
                if "CT" in scan_type or "PT" in scan_type:
                    pet_results.update(result)
                elif scan_type=="MR":
                    mri_results.update(result)
        except pydicom.errors.InvalidDicomError:
            if parent_file.endswith(".iso"):
                unmount_iso(mount_location)
            pass
        except Exception as e:
            if parent_file.endswith(".iso"):
                unmount_iso(mount_location)
            logging.info("failed")
            logging.debug(e)
    else:
        for path, subdirs, files in os.walk(parent_file):
            for name in files:
                working_file = os.path.join(path, name)
                try:
                    if name.endswith(".iso"):
                        top_dir = mount_iso(working_file, mount_location)
                        walk(top_dir, pet_values, mri_values)
                        unmount_iso(mount_location)
                    else:
                        logging.info("Working on: " + working_file)
                        result, scan_type = read_dicom(working_file)
                        if "CT" in scan_type or "PT" in scan_type:
                            pet_results.update(result)
                        elif scan_type=="MR":
                            mri_results.update(result)
                except pydicom.errors.InvalidDicomError:
                    if name.endswith(".iso"):
                        unmount_iso(mount_location)
                    continue
                except Exception as e:
                    if name.endswith(".iso"):
                        unmount_iso(mount_location)
                    logging.info("failed")
                    logging.debug(e)
    pet_values.extend(pet_results.values())
    mri_values.extend(mri_results.values())


def read_dicom(dicom_file):
    info = {}
    dataset =  pydicom.read_file(dicom_file)
    tags = dataset.dir()
    for tag in tags:
        value = getattr(dataset, tag, None)
        if type(value) is pydicom.sequence.Sequence:
            continue
        elif type(value) is bytes:
            continue
        else:
            info[tag] = value 
    key = dataset.PatientID + '_' + dataset.StudyDate
    return ({key: info}, dataset.Modality)


def main(args):
    if not os.path.exists('data_out'):
        os.mkdir('data_out')
    date = datetime.datetime.now().strftime("%Y_%m_%d")
    if not os.path.exists('data_out/' + date):
        os.mkdir('data_out/' + date)
    log_file = os.path.join('data_out', date, date + '_log.txt')
    logging.basicConfig(filename=log_file, level=logging.DEBUG)

    # Navigate provided file or folder to get tags for each dicom image
    pet_rows = []
    mri_rows = []
    walk(args[DICOM_PATH], pet_rows, mri_rows)

    # Pull out tag names to become headers in csv
    pet_columns = []
    mri_columns = []
    for row in pet_rows:
        for tag in row.keys():
            if tag not in pet_columns:
                pet_columns.append(tag)
    for row in mri_rows:
        for tag in row.keys():
            if tag not in mri_columns:
                mri_columns.append(tag)

    pet_out = "data_out/" + date + "/pet_tags_" + date + ".csv"
    mri_out = "data_out/" + date + "/mri_tags_" + date + ".csv"

    # Building off pre-existing pet file
    if args[PET_FILE]:
        with open(args[PET_FILE], 'r') as old_pet:
            old_pet_rows = []
            pet_reader = csv.reader(old_pet)
            old_pet_headers = next(pet_reader)
            for row in pet_reader:
                old_pet_rows.append(dict(zip(old_pet_headers, row)))
        for row in old_pet_rows:
            if row not in pet_rows:
                pet_rows.append(row)
        for header in old_pet_headers:
            if header not in pet_columns:
                pet_columns.append(header)

    # Create pet file
    with open(pet_out, 'w') as pet_csv:
        pet_writer = csv.DictWriter(pet_csv, fieldnames=pet_columns)
        pet_writer.writeheader()
        for row in pet_rows:
            pet_writer.writerow(row)

    # Building off pre-existing mri file
    if args[MRI_FILE]:
        with open(args[MRI_FILE], 'r') as old_mri:
            old_mri_rows = []
            mri_reader = csv.reader(old_mri)
            old_mri_headers = next(mri_reader)
            for row in mri_reader:
                old_mri_rows.append(dict(zip(old_mri_headers, row)))
        for row in old_mri_rows:
            if row not in mri_rows:
                mri_rows.append(row)
        for header in old_mri_headers:
            if header not in mri_columns:
                mri_columns.append(header)

    # Create mri file
    with open(mri_out, 'w') as mri_csv:
        mri_writer = csv.DictWriter(mri_csv, fieldnames=mri_columns)
        mri_writer.writeheader()
        for row in mri_rows:
            mri_writer.writerow(row)


if __name__ == '__main__':
    args = docopt(docstr)
    main(args)