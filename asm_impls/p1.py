import argparse
import subprocess


class AugmentationError(Exception):
    pass


def augment_line(r, m, line):
    command = ["./augmenter", "0x0", str(r), str(m), line]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = process.communicate()

    print(stderr, end="")

    if process.returncode != 0:
        raise AugmentationError(f"Error: {stderr}")
    else:
        return stdout


def augment_lines_from_file(r: int, m: int, filename: str):
    content: str = ""

    with open(filename, "r") as file:
        for line in file:
            line = line.split("//")[0].strip()
            if len(line) == 0:
                continue
            output = augment_line(r, m, line).strip()
            print(line, ":", output)
            if output.startswith("0xb"):
                content += output[3:]
            elif output.startswith("0x"):
                for d in output[2:]:
                    content += f"{int(d, base=16):04b}"
            else:
                raise ValueError(output)

    # Adjust the last byte and write to the binary file
    while len(content) % 8 != 0:
        content += "0"  # Fill the remaining bits with zeros

    # Convert binary content to bytes
    binary_bytes = bytes(int(content[i : i + 8], 2) for i in range(0, len(content), 8))

    # Write to the binary file
    with open(filename + ".bin", "wb") as binary_file:
        binary_file.write(binary_bytes)

    print("Augmentation complete.")

    l = len(binary_bytes)
    print(f"Size: {l} byte{'s' if l > 10 and l % 10 != 1 else ''}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Augment lines from a file using a command."
    )
    parser.add_argument(
        "--r",
        type=int,
        help="The register span (where there are 2^r registers) (int >= 1)",
        default=3,
    )
    parser.add_argument(
        "--m",
        type=int,
        help="The address space (where mem is of 2^2^m bits) (int >= 1)",
        default=4,
    )
    parser.add_argument("filename", type=str, help="The path to the input file.")

    args = parser.parse_args()
    augment_lines_from_file(args.r, args.m, args.filename)
