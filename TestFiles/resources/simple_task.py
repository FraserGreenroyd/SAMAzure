import os


if __name__ == '__main__':
    print("simpletask.py listing files:")
    for item in os.listdir('.'):
        print(item)
