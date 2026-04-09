# Basic8 CPU

![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

- [Read the documentation for project](docs/info.md)

## Architecture

Basic8 is a minimal single-cycle 8-bit processor. It features 8 general-purpose 8-bit registers (r0–r7); r0 is hardwired to zero. All arithmetic and logic operations pass through a single ALU. For R-type instructions the second operand comes from a source register; for I-type instructions it comes from the sign-extended 6-bit immediate. The ALU operation is selected via a 3-bit funct3 signal — taken directly from the instruction for R-type, and derived from the opcode for I-type.

Instructions and data share a single external memory bus (e.g. SPI Flash). The CPU outputs a memory address on `uo_out` and receives a byte on `ui_in`. During normal execution this address is the PC; during LOAD/STORE it is the computed data address (`rs1 + sign_ext(imm6)`).

Since instructions are 16-bit wide, they are loaded in two cycles:
- **Cycle 1:** `uio_in[0]=1` — `ui_in` high byte is latched into `instr_hi`
- **Cycle 2:** `uio_in[1]=1` — `ui_in` low byte is combined with `instr_hi` to form the full 16-bit instruction, which is then decoded and executed

For LOAD, the CPU stalls (holds PC) until the external controller asserts `mem_valid` (`uio_in[3]=1`), then writes `ui_in` into the destination register and advances PC. For STORE, the CPU drives the data address on `uo_out` and the source register value on `uio_out`, and asserts `mem_we` (`uio_out` side, indicated by the STORE exec cycle) for one cycle; PC then advances immediately.

## Instruction Set

| Opcode | Instr | Bit Layout | Operation |
|--------|-------|-----------|-----------|
| `0000` (f3=000) | ADD  | `[15:13]=f3 [12:10]=rs2 [9:7]=rs1 [6:4]=rd [3:0]=0000` | `rd = rs1 + rs2` |
| `0000` (f3=001) | SUB  | `[15:13]=f3 [12:10]=rs2 [9:7]=rs1 [6:4]=rd [3:0]=0000` | `rd = rs1 - rs2` |
| `0000` (f3=010) | OR   | `[15:13]=f3 [12:10]=rs2 [9:7]=rs1 [6:4]=rd [3:0]=0000` | `rd = rs1 \| rs2` |
| `0000` (f3=011) | XOR  | `[15:13]=f3 [12:10]=rs2 [9:7]=rs1 [6:4]=rd [3:0]=0000` | `rd = rs1 ^ rs2` |
| `0000` (f3=100) | AND  | `[15:13]=f3 [12:10]=rs2 [9:7]=rs1 [6:4]=rd [3:0]=0000` | `rd = rs1 & rs2` |
| `0000` (f3=101) | SLL  | `[15:13]=f3 [12:10]=rs2 [9:7]=rs1 [6:4]=rd [3:0]=0000` | `rd = rs1 << rs2` |
| `0000` (f3=110) | SRL  | `[15:13]=f3 [12:10]=rs2 [9:7]=rs1 [6:4]=rd [3:0]=0000` | `rd = rs1 >> rs2` |
| `0000` (f3=111) | SRA  | `[15:13]=f3 [12:10]=rs2 [9:7]=rs1 [6:4]=rd [3:0]=0000` | `rd = rs1 >>> rs2` |
| `0001` | ADDI | `[15:10]=imm6 [9:7]=rs1 [6:4]=rd [3:0]=0001` | `rd = rs1 + sign_ext(imm6)` |
| `0010` | ANDI | `[15:10]=imm6 [9:7]=rs1 [6:4]=rd [3:0]=0010` | `rd = rs1 & sign_ext(imm6)` |
| `0011` | ORI  | `[15:10]=imm6 [9:7]=rs1 [6:4]=rd [3:0]=0011` | `rd = rs1 \| sign_ext(imm6)` |
| `0100` | XORI | `[15:10]=imm6 [9:7]=rs1 [6:4]=rd [3:0]=0100` | `rd = rs1 ^ sign_ext(imm6)` |
| `0101` | BEQ  | `[15:10]=imm6 [9:7]=rs1 [6:4]=rs2 [3:0]=0101` | `if rs1==rs2: PC = PC + sign_ext(imm6)` |
| `0110` | BNE  | `[15:10]=imm6 [9:7]=rs1 [6:4]=rs2 [3:0]=0110` | `if rs1!=rs2: PC = PC + sign_ext(imm6)` |
| `0111` | JAL  | `[15:10]=imm6 [9:7]=--- [6:4]=rd  [3:0]=0111` | `rd = PC+1, PC = PC + sign_ext(imm6)` |
| `1000` | LOAD | `[15:10]=imm6 [9:7]=rs1 [6:4]=rd  [3:0]=1000` | `rd = mem[rs1 + sign_ext(imm6)]` |
| `1001` | STORE| `[15:10]=imm6 [9:7]=rs1 [6:4]=rs2 [3:0]=1001` | `mem[rs1 + sign_ext(imm6)] = rs2` |

> **imm6:** 6-bit signed immediate, always sign-extended to 8 bits. **f3** = funct3 field `[15:13]`, selects ALU operation for R-type instructions.

## Pin Interface

| Pin | Direction | Description |
|-----|-----------|-------------|
| `ui_in[7:0]`  | Input  | Memory data in — instruction byte or LOAD data |
| `uo_out[7:0]` | Output | Memory address — PC during fetch, `rs1+imm` during LOAD/STORE |
| `uio_in[0]`   | Input  | `load_hi` — latch `ui_in` as instruction high byte |
| `uio_in[1]`   | Input  | `exec` — decode and execute latched instruction |
| `uio_in[3]`   | Input  | `mem_valid` — external memory data ready (used to end LOAD stall) |
| `uio_out[7:0]`| Output | STORE data — `rs2` value, valid when STORE exec cycle is active |

---

↓ ↓ ↓

---

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that aims to make it easier and cheaper than ever to get your digital and analog designs manufactured on a real chip.

To learn more and get started, visit https://tinytapeout.com.

## Set up your Verilog project

1. Add your Verilog files to the `src` folder.
2. Edit the [info.yaml](info.yaml) and update information about your project, paying special attention to the `source_files` and `top_module` properties. If you are upgrading an existing Tiny Tapeout project, check out our [online info.yaml migration tool](https://tinytapeout.github.io/tt-yaml-upgrade-tool/).
3. Edit [docs/info.md](docs/info.md) and add a description of your project.
4. Adapt the testbench to your design. See [test/README.md](test/README.md) for more information.

The GitHub action will automatically build the ASIC files using [LibreLane](https://www.zerotoasiccourse.com/terminology/librelane/).

## Enable GitHub actions to build the results page

- [Enabling GitHub Pages](https://tinytapeout.com/faq/#my-github-action-is-failing-on-the-pages-part)

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Learn how semiconductors work](https://tinytapeout.com/siliwiz/)
- [Join the community](https://tinytapeout.com/discord)
- [Build your design locally](https://www.tinytapeout.com/guides/local-hardening/)

## What next?

- [Submit your design to the next shuttle](https://app.tinytapeout.com/).
- Edit [this README](README.md) and explain your design, how it works, and how to test it.
- Share your project on your social network of choice:
  - LinkedIn [#tinytapeout](https://www.linkedin.com/search/results/content/?keywords=%23tinytapeout) [@TinyTapeout](https://www.linkedin.com/company/100708654/)
  - Mastodon [#tinytapeout](https://chaos.social/tags/tinytapeout) [@matthewvenn](https://chaos.social/@matthewvenn)
  - X (formerly Twitter) [#tinytapeout](https://twitter.com/hashtag/tinytapeout) [@tinytapeout](https://twitter.com/tinytapeout)
  - Bluesky [@tinytapeout.com](https://bsky.app/profile/tinytapeout.com)
