# ActiFuzz
ActiFuzz is an Android intent fuzzing python script for exported activities that take extras as inputs.

## Prerequisites

- Python3
- adb
- argparse
- colorama

## Install

```
$ git clone https://github.com/mathis2001/ActiFuzz
$ cd Actifuzz
$ chmod +x actifuzz.py
```

## Usage

```
$ ./actifuzz.py [-h] -a ACTIVITY [-s SERIAL] [-d DATA] [--str STR] [--int INT] [--bool BOOL] [--float FLOAT] [--long LONG] [-D DELAY] [-w WORDLIST]
```

### Send Custom Intent

```
$ ./actifuzz.py -a com.example.xyz/.MainActivity  [-d DATA] --str sextra=string --int iextra=int --bool bextra=bool --float fextra=float --long lextra=long
```

### Fuzz Intent (with default wordlist)

```
$ ./actifuzz.py -a com.example.xyz/.MainActivity [-d DATA]--str sextra=FUZZ --int iextra=FUZZ --bool bextra=FUZZ --float fextra=FUZZ --long lextra=FUZZ [-D delay]
```

### Fuzz Intent (with custom wordlist)

```
$ ./actifuzz.py -a com.example.xyz/.MainActivity [-d DATA] --str sextra=FUZZ --int iextra=FUZZ --bool bextra=FUZZ --float fextra=FUZZ --long lextra=FUZZ -w path/to/wordlist [-d delay]
```

## Options

```
options:
  -h, --help            show this help message and exit
  -a ACTIVITY, --activity ACTIVITY
                        Full activity name (e.g. com.example/.MainActivity)
  -s SERIAL, --serial SERIAL
                        Device serial number
  --str STR             String extra (format key=value)
  --int INT             Integer extra (format key=value)
  --bool BOOL           Boolean extra (format key=true/false)
  --float FLOAT         Float extra (format key=value)
  --long LONG           Long extra (format key=value)
  -d DATA, --data DATA
                        Data to pass to 'am start' as -d (supports FUZZ)
  -D DELAY, --delay DELAY
                        Set the delay between adb commands (seconds)
  -w WORDLIST, --wordlist WORDLIST
                        Path to a wordlist file to use as FUZZ payloads (one per line).
```

## Screenshots

## To Do

- Generate all possible variations
- Potentially add a screenshot feature to store UI previews
