import argparse
import subprocess
import time
import sys
from pathlib import Path
from colorama import Fore

def banner():
    print("""
                                                                          
             @@@@@@    @@@@@@@  @@@@@@@  @@@  @@@@@@@@  @@@  @@@  @@@@@@@@  @@@@@@@@  
            @@@@@@@@  @@@@@@@@  @@@@@@@  @@@  @@@@@@@@  @@@  @@@  @@@@@@@@  @@@@@@@@  
            @@!  @@@  !@@         @@!    @@!  @@!       @@!  @@@       @@!       @@!  
            !@!  @!@  !@!         !@!    !@!  !@!       !@!  @!@      !@!       !@!   
            @!@!@!@!  !@!         @!!    !!@  @!!!:!    @!@  !@!     @!!       @!!    
            !!!@!!!!  !!!         !!!    !!!  !!!!!:    !@!  !!!    !!!       !!!     
            !!:  !!!  :!!         !!:    !!:  !!:       !!:  !!!   !!:       !!:      
            :!:  !:!  :!:         :!:    :!:  :!:       :!:  !:!  :!:       :!:       
            ::   :::   ::: :::     ::     ::   ::       ::::: ::   :: ::::   :: ::::  
             :   : :   :: :: :     :     :     :         : :  :   : :: : :  : :: : :  
                                                                  By S1rN3tZ
        """)

def parse_cli_args():
    parser = argparse.ArgumentParser(description="Run an ADB activity with typed extras and FUZZ support.")
    parser.add_argument("-a", "--activity", required=True, help="Full activity name (e.g. com.example/.MainActivity)")
    parser.add_argument("-s", "--serial", help="Device serial number")

    # Note: moved delay to -D / --delay to free -d for --data per requested behavior
    parser.add_argument("-D", "--delay", help="Set the delay between adb commands (seconds)")
    parser.add_argument("-d", "--data", help="Data URI to pass to 'am start' as -d (supports FUZZ)")

    parser.add_argument("--str", action="append", help="String extra (format key=value)")
    parser.add_argument("--int", action="append", help="Integer extra (format key=value)")
    parser.add_argument("--bool", action="append", help="Boolean extra (format key=true/false)")
    parser.add_argument("--float", action="append", help="Float extra (format key=value)")
    parser.add_argument("--long", action="append", help="Long extra (format key=value)")

    parser.add_argument("-w", "--wordlist", help="Path to a wordlist file to use as FUZZ payloads (one per line). Lines starting with # or blank lines are ignored.")

    return parser.parse_args()

def run_adb_activity(activity, extras=None, serial=None, delay=None, data=None):
    """
    Run an ADB activity command with optional extras and optional -d <data>.
    Supports extras of type str (-es), int (-ei), bool (-ez), float (-ef), long (-el).
    """
    base_cmd = ["adb"]
    if serial:
        base_cmd += ["-s", serial]

    # Build am start command: include -d <data> before -n if provided
    cmd = ["shell", "am", "start"]
    if data:
        cmd += ["-d", data]
    cmd += ["-n", activity]

    if extras:
        for key, value in extras.items():
            if isinstance(value, str):
                cmd += ["-es", key, value]
            elif isinstance(value, bool):
                cmd += ["-ez", key, str(value).lower()]
            elif isinstance(value, int):
                cmd += ["-ei", key, str(value)]
            elif isinstance(value, float):
                cmd += ["-ef", key, str(value)]
            else:
                raise TypeError(f"{Fore.RED}[!]{Fore.RESET} Unsupported extra type for {key}: {type(value).__name__}")

    full_cmd = base_cmd + cmd
    jcmd = " ".join(full_cmd)

    print(f"\n{Fore.CYAN}[*]{Fore.RESET} Running command: {Fore.CYAN}{jcmd}{Fore.RESET}")
    try:
        output = subprocess.check_output(full_cmd, stderr=subprocess.STDOUT).decode("utf-8")
        print(output.strip())

        if delay:
            try:
                time.sleep(int(delay))
            except Exception:
                time.sleep(0.5)
        else:
            time.sleep(0.5)

        # Send BACK keyevent after successful launch
        back_cmd = base_cmd + ["shell", "input", "keyevent", "4"]
        subprocess.run(back_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8")


def parse_key_value_pairs(pairs, declared_type):
    """
    Function to parse key=value pairs corresponding to extras name:value.
    """
    if not pairs:
        return {}
    extras = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"{Fore.RED}[!]{Fore.RESET} Invalid format: {pair}. Expected key=value")
        key, value = pair.split("=", 1)
        # Don't cast yet if FUZZ is in value
        if "FUZZ" in value:
            extras[key] = value  # keep as string
        else:
            try:
                if declared_type == bool:
                    extras[key] = value.lower() in ["true", "1", "yes"]
                else:
                    extras[key] = declared_type(value)
            except ValueError:
                # fallback to string if cast fails
                extras[key] = value
    return extras


def load_wordlist(path):
    """
    Function to load a custom wordlist when the fuzzing feature is used.
    """
    p = Path(path)
    if not p.is_file():
        print(f"{Fore.RED}[!]{Fore.RESET} Error: wordlist file not found: {path}", file=sys.stderr)
        sys.exit(2)
    payloads = []
    try:
        with p.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                # Delete \n\r at the end of each lines
                line = line.rstrip("\n\r")
                # ignore blank lines
                if not line:
                    continue
                # ignore comment lines that start with #
                if line.lstrip().startswith("#"):
                    continue
                payloads.append(line)
    except Exception as e:
        print(f"{Fore.RED}[!]{Fore.RESET} Error reading wordlist file: {e}", file=sys.stderr)
        sys.exit(2)

    if not payloads:
        print(f"{Fore.ORANGE}[-]{Fore.RESET} Warning: wordlist '{path}' contained no usable payloads; falling back to built-in list.", file=sys.stderr)
    else:
        print(f"{Fore.GREEN}[+]{Fore.RESET} Loaded {len(payloads)} payloads from wordlist: {path}")
    return payloads


def fuzz_extras(extras, wordlist=None):
    """
    Function to detect and fuzz any value containing 'FUZZ'.
    If wordlist is provided (list), use it; otherwise use the built-in fuzz_values.
    Returns a list of extras dicts (one per variation).
    """
    default_fuzz_values = [
        "", " ", "null", "None", "0", "-1", "9999999999",
        "!@#$%^&*()", "A" * 100, "A" * 5000, "<script>alert(1)</script>", "🔥", "\n\t",
    ]

    fuzz_values = wordlist if (wordlist and len(wordlist) > 0) else default_fuzz_values

    fuzz_targets = {k: v for k, v in extras.items() if isinstance(v, str) and "FUZZ" in v}
    if not fuzz_targets:
        return [extras]  # no fuzzing needed

    fuzzed_list = []
    for payload in fuzz_values:
        new_extras = extras.copy()
        for key, value in fuzz_targets.items():
            new_extras[key] = value.replace("FUZZ", payload)
        fuzzed_list.append(_convert_types_after_fuzz(new_extras))

    print(f"{Fore.GREEN}[+]{Fore.RESET} FUZZ detected for {Fore.GREEN}{', '.join(fuzz_targets.keys())}{Fore.RESET} → {Fore.CYAN}{len(fuzzed_list)}{Fore.RESET} variations generated")
    return fuzzed_list


def _convert_types_after_fuzz(extras):
    """
    After fuzz replacement, try to convert non-FUZZ values to proper numeric/bool types.
    """
    converted = {}
    for k, v in extras.items():
        # skip non-strings
        if not isinstance(v, str):
            converted[k] = v
            continue

        lower = v.lower()
        if lower in ["true", "false"]:
            converted[k] = lower == "true"
        else:
            try:
                # Attempt integer first if no dot, otherwise float
                if "." in v:
                    converted[k] = float(v)
                else:
                    converted[k] = int(v)
            except ValueError:
                converted[k] = v  # leave as string if conversion fails
    return converted


def main():
    banner()
    args = parse_cli_args()

    # Merge all extras
    extras = {}
    extras.update(parse_key_value_pairs(args.str, str))
    extras.update(parse_key_value_pairs(args.int, int))
    extras.update(parse_key_value_pairs(args.bool, bool))
    extras.update(parse_key_value_pairs(args.float, float))
    extras.update(parse_key_value_pairs(args.long, int))  # long = int in Python 3

    # Load wordlist if requested
    wordlist_payloads = None
    if args.wordlist:
        wordlist_payloads = load_wordlist(args.wordlist)

    # Fuzz extras if needed
    extras_variants = fuzz_extras(extras, wordlist_payloads)

    # Handle FUZZ inside --data (if present). Make cross-product of extras_variants x data_variants
    default_fuzz_values = [
        "", " ", "null", "None", "0", "-1", "9999999999",
        "!@#$%^&*()", "A" * 100, "A" * 5000, "<script>alert(1)</script>", "🔥", "\n\t",
    ]
    data_variants = []
    if args.data and "FUZZ" in args.data:
        fuzz_values = wordlist_payloads if (wordlist_payloads and len(wordlist_payloads) > 0) else default_fuzz_values
        for payload in fuzz_values:
            data_variants.append(args.data.replace("FUZZ", payload))
        print(f"{Fore.GREEN}[+]{Fore.RESET} FUZZ detected in --data → {Fore.CYAN}{len(data_variants)}{Fore.RESET} data variations generated")
    else:
        # single data value (may be None)
        data_variants = [args.data]

    # Build combined list of (extras_variant, data_variant) pairs
    combined = []
    for ex in extras_variants:
        for dv in data_variants:
            combined.append((ex, dv))

    # If no fuzzing occurred at all and neither extras nor data had FUZZ, combined will contain one element.
    for idx, (variant_extras, variant_data) in enumerate(combined, start=1):
        print(f"\n=== Fuzzing Intent {idx}/{len(combined)} ===")
        run_adb_activity(args.activity, variant_extras, args.serial, args.delay, data=variant_data)


if __name__ == "__main__":
    main()
