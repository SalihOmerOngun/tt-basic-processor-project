import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


def _imm6(val):
    return val & 0x3F

def R(funct3, rd, rs1, rs2):
    return (funct3 << 13) | (rs2 << 10) | (rs1 << 7) | (rd << 4) | 0b0000

def ADDI(rd, rs1, imm):
    return (_imm6(imm) << 10) | (rs1 << 7) | (rd << 4) | 0b0001

def ANDI(rd, rs1, imm):
    return (_imm6(imm) << 10) | (rs1 << 7) | (rd << 4) | 0b0010

def ORI(rd, rs1, imm):
    return (_imm6(imm) << 10) | (rs1 << 7) | (rd << 4) | 0b0011

def XORI(rd, rs1, imm):
    return (_imm6(imm) << 10) | (rs1 << 7) | (rd << 4) | 0b0100

def BEQ(rs1, rs2, imm):
    return (_imm6(imm) << 10) | (rs1 << 7) | (rs2 << 4) | 0b0101

def BNE(rs1, rs2, imm):
    return (_imm6(imm) << 10) | (rs1 << 7) | (rs2 << 4) | 0b0110

def JAL(rd, imm):
    return (_imm6(imm) << 10) | (rd << 4) | 0b0111

def LOAD(rd, rs1, imm):
    return (_imm6(imm) << 10) | (rs1 << 7) | (rd << 4) | 0b1000

def STORE(rs2, rs1, imm):
    return (_imm6(imm) << 10) | (rs1 << 7) | (rs2 << 4) | 0b1001

def NOP():
    return ADDI(0, 0, 0)

ADD  = 0b000
SUB  = 0b001
F_OR = 0b010
XOR  = 0b011
AND  = 0b100
SLL  = 0b101
SRL  = 0b110
SRA  = 0b111

async def do_reset(dut):
    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

async def send_instr(dut, instr):
    hi = (instr >> 8) & 0xFF
    lo =  instr       & 0xFF

    await FallingEdge(dut.clk)
    dut.ui_in.value  = hi
    dut.uio_in.value = 0b00000001
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    await FallingEdge(dut.clk)
    dut.ui_in.value  = lo
    dut.uio_in.value = 0b00000010
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    await FallingEdge(dut.clk)
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await Timer(1, unit="ns")

async def send_instr_then_load_data(dut, instr, data_byte):
    """LOAD komutu gönderir, ardından mem_valid ile veriyi sunar."""
    hi = (instr >> 8) & 0xFF
    lo =  instr       & 0xFF

    await FallingEdge(dut.clk)
    dut.ui_in.value  = hi
    dut.uio_in.value = 0b00000001
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    await FallingEdge(dut.clk)
    dut.ui_in.value  = lo
    dut.uio_in.value = 0b00000010
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    # exec posedge'de mem_wait set oldu, bir cycle bos bekliyoruz
    await FallingEdge(dut.clk)
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    # Simdi mem_valid verebiliriz
    await FallingEdge(dut.clk)
    dut.ui_in.value  = data_byte
    dut.uio_in.value = 0b00001000   # mem_valid = uio_in[3]
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    await FallingEdge(dut.clk)
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await Timer(1, unit="ns")

async def read_reg(dut, idx):
    try:
        return int(dut.user_project.regfile[idx].value)
    except AttributeError:
        dut.ui_in.value = (idx & 0x7) << 4
        await Timer(2, unit="ns")
        return int(dut.uio_out.value)

async def run_rom(dut, rom, cycles):
    for _ in range(cycles):
        pc    = int(dut.uo_out.value)
        instr = rom[pc] if pc < len(rom) else NOP()
        await send_instr(dut, instr)


async def check_i_type(dut):
    dut._log.info("--- I-type: ADDI, ANDI, ORI, XORI ---")
    rom = [NOP()] * 256
    rom[0] = ADDI(1, 0,  5)
    rom[1] = ADDI(2, 0,  3)
    rom[2] = ADDI(3, 1, 10)
    rom[3] = ANDI(4, 3,  6)
    rom[4] = ORI (5, 0, 12)
    rom[5] = XORI(6, 5,  5)
    rom[6] = NOP()

    await do_reset(dut)
    await run_rom(dut, rom, 7)

    assert await read_reg(dut, 1) ==  5, "ADDI r1=5 failed"
    assert await read_reg(dut, 2) ==  3, "ADDI r2=3 failed"
    assert await read_reg(dut, 3) == 15, "ADDI r3=15 failed"
    assert await read_reg(dut, 4) ==  6, "ANDI r4=6 failed"
    assert await read_reg(dut, 5) == 12, "ORI  r5=12 failed"
    assert await read_reg(dut, 6) ==  9, "XORI r6=9 failed"
    dut._log.info("I-type PASSED")

async def check_r_type(dut):
    dut._log.info("--- R-type: ADD, SUB, AND, OR, XOR, SLL, SRL ---")
    rom = [NOP()] * 256
    rom[0] = ADDI(1, 0, 5)
    rom[1] = ADDI(2, 0, 3)
    rom[2] = R(ADD,   3, 1, 2)
    rom[3] = R(SUB,   4, 3, 2)
    rom[4] = R(AND,   5, 1, 2)
    rom[5] = R(F_OR,  6, 1, 2)
    rom[6] = R(XOR,   7, 1, 2)
    rom[7] = R(SLL,   3, 2, 2)
    rom[8] = R(SRL,   3, 3, 2)
    rom[9] = NOP()

    await do_reset(dut)
    await run_rom(dut, rom, 10)

    assert await read_reg(dut, 4) == 5, "SUB failed"
    assert await read_reg(dut, 5) == 1, "AND failed"
    assert await read_reg(dut, 6) == 7, "OR  failed"
    assert await read_reg(dut, 7) == 6, "XOR failed"
    assert await read_reg(dut, 3) == 3, "SLL+SRL failed"
    dut._log.info("R-type PASSED")

async def check_addi_negative(dut):
    dut._log.info("--- ADDI negative immediate ---")
    rom = [NOP()] * 256
    rom[0] = ADDI(1, 0, -1)    # r1 = 0xFF
    rom[1] = ADDI(2, 0, -8)    # r2 = 0xF8
    rom[2] = NOP()

    await do_reset(dut)
    await run_rom(dut, rom, 3)

    assert await read_reg(dut, 1) == 0xFF, "ADDI -1 failed"
    assert await read_reg(dut, 2) == 0xF8, "ADDI -8 failed"
    dut._log.info("ADDI negative PASSED")

async def check_beq(dut):
    dut._log.info("--- BEQ taken / not taken ---")
    rom = [NOP()] * 256
    rom[0] = ADDI(1, 0, 5)
    rom[1] = ADDI(2, 0, 5)
    rom[2] = ADDI(3, 0, 0)
    rom[3] = BEQ(1, 2, 2)
    rom[4] = ADDI(3, 0, 20)
    rom[5] = ADDI(4, 0, 7)
    rom[6] = NOP()

    await do_reset(dut)
    await run_rom(dut, rom, 7)

    assert await read_reg(dut, 3) ==  0, "BEQ: r3 should be skipped"
    assert await read_reg(dut, 4) ==  7, "BEQ: r4=7 after jump"
    dut._log.info("BEQ PASSED")

async def check_bne_loop(dut):
    dut._log.info("--- BNE backward loop (count 0->3) ---")
    rom = [NOP()] * 256
    rom[0] = ADDI(1, 0, 0)
    rom[1] = ADDI(2, 0, 3)
    rom[2] = ADDI(3, 0, 1)
    rom[3] = R(ADD, 1, 1, 3)
    rom[4] = BNE(1, 2, -1)
    rom[5] = NOP()

    await do_reset(dut)
    await run_rom(dut, rom, 20)

    assert await read_reg(dut, 1) == 3, "BNE loop: r1 should be 3"
    dut._log.info("BNE loop PASSED")

async def check_jal(dut):
    dut._log.info("--- JAL: jump and link ---")
    rom = [NOP()] * 256
    rom[0] = ADDI(1, 0, 1)
    rom[1] = ADDI(2, 0, 2)
    rom[2] = JAL(5, 3)
    rom[3] = ADDI(3, 0, 20)
    rom[4] = ADDI(4, 0, 20)
    rom[5] = ADDI(6, 0, 15)
    rom[6] = NOP()

    await do_reset(dut)
    await run_rom(dut, rom, 7)

    assert await read_reg(dut, 5) ==  3, "JAL: return addr r5=3"
    assert await read_reg(dut, 3) ==  0, "JAL: r3 skipped"
    assert await read_reg(dut, 4) ==  0, "JAL: r4 skipped"
    assert await read_reg(dut, 6) == 15, "JAL: r6=15 after jump"
    dut._log.info("JAL PASSED")

async def check_r0_hardwired(dut):
    dut._log.info("--- r0 hardwired to 0 ---")
    rom = [NOP()] * 256
    rom[0] = ADDI(0, 0, 9)
    rom[1] = NOP()

    await do_reset(dut)
    await run_rom(dut, rom, 2)

    assert await read_reg(dut, 0) == 0, "r0 must be hardwired 0"
    dut._log.info("r0 hardwired PASSED")

async def setup_base_addr(dut, reg_idx):
    """reg_idx'e 0x80 yukler: ADDI r,r0,1 sonra 7x ADD r,r,r"""
    await send_instr(dut, ADDI(reg_idx, 0, 1))
    for _ in range(7):
        await send_instr(dut, R(ADD, reg_idx, reg_idx, reg_idx))

async def exec_store(dut, instr):
    """STORE komutunu gonderir, exec cycle'da pin degerlerini dondurur."""
    hi = (instr >> 8) & 0xFF
    lo =  instr       & 0xFF

    await FallingEdge(dut.clk)
    dut.ui_in.value  = hi
    dut.uio_in.value = 0b00000001
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    await FallingEdge(dut.clk)
    dut.ui_in.value  = lo
    dut.uio_in.value = 0b00000010
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    addr = int(dut.uo_out.value)
    data = int(dut.uio_out.value)

    await FallingEdge(dut.clk)
    dut.uio_in.value = 0
    await Timer(1, unit="ns")

    return addr, data

async def check_load(dut):
    dut._log.info("--- LOAD: mem[rs1+imm] -> rd ---")
    await do_reset(dut)

    await setup_base_addr(dut, 1)
    assert await read_reg(dut, 1) == 0x80, "LOAD setup: r1=0x80 failed"

    # offset=0
    await send_instr_then_load_data(dut, LOAD(2, 1, 0), 0xAB)
    assert await read_reg(dut, 2) == 0xAB, "LOAD offset=0 failed"

    # offset=1
    await send_instr_then_load_data(dut, LOAD(3, 1, 1), 0xCD)
    assert await read_reg(dut, 3) == 0xCD, "LOAD offset=1 failed"

    # offset pozitif max (imm6=31 -> 0x80+31=0x9F)
    await send_instr_then_load_data(dut, LOAD(4, 1, 31), 0x12)
    assert await read_reg(dut, 4) == 0x12, "LOAD offset=31 failed"

    # negatif offset (-1 -> 0x7F, instruction space sonu)
    await send_instr_then_load_data(dut, LOAD(5, 1, -1), 0x34)
    assert await read_reg(dut, 5) == 0x34, "LOAD offset=-1 failed"

    # r0'a LOAD: deger yazilmamali
    await send_instr_then_load_data(dut, LOAD(0, 1, 0), 0xFF)
    assert await read_reg(dut, 0) == 0x00, "LOAD into r0 must be discarded"

    # farkli veri degerleri: 0x00 ve 0xFF
    await send_instr_then_load_data(dut, LOAD(6, 1, 2), 0x00)
    assert await read_reg(dut, 6) == 0x00, "LOAD data=0x00 failed"

    await send_instr_then_load_data(dut, LOAD(7, 1, 3), 0xFF)
    assert await read_reg(dut, 7) == 0xFF, "LOAD data=0xFF failed"

    dut._log.info("LOAD PASSED")

async def check_store(dut):
    dut._log.info("--- STORE: rs2 -> mem[rs1+imm] ---")
    await do_reset(dut)

    await setup_base_addr(dut, 1)
    assert await read_reg(dut, 1) == 0x80, "STORE setup: r1=0x80 failed"

    # r2 = 0x55
    await send_instr(dut, ADDI(2, 0, 0x15))
    await send_instr(dut, R(ADD, 2, 2, 2))
    await send_instr(dut, R(ADD, 2, 2, 2))
    await send_instr(dut, ADDI(2, 2, 1))
    assert await read_reg(dut, 2) == 0x55, "STORE setup: r2=0x55 failed"

    # offset=2: adres 0x82, data 0x55
    addr, data = await exec_store(dut, STORE(2, 1, 2))
    assert addr == 0x82, f"STORE offset=2 addr: beklenen 0x82, gelen {hex(addr)}"
    assert data == 0x55, f"STORE offset=2 data: beklenen 0x55, gelen {hex(data)}"

    # offset=0: adres 0x80
    addr, data = await exec_store(dut, STORE(2, 1, 0))
    assert addr == 0x80, f"STORE offset=0 addr: beklenen 0x80, gelen {hex(addr)}"
    assert data == 0x55, f"STORE offset=0 data: beklenen 0x55, gelen {hex(data)}"

    # negatif offset (-1 -> 0x7F)
    addr, data = await exec_store(dut, STORE(2, 1, -1))
    assert addr == 0x7F, f"STORE offset=-1 addr: beklenen 0x7F, gelen {hex(addr)}"
    assert data == 0x55, f"STORE offset=-1 data: beklenen 0x55, gelen {hex(data)}"

    # r3 = 0x00, STORE data=0x00
    await send_instr(dut, ADDI(3, 0, 0))
    addr, data = await exec_store(dut, STORE(3, 1, 0))
    assert data == 0x00, f"STORE data=0x00: beklenen 0x00, gelen {hex(data)}"

    # r4 = 0xFF, STORE data=0xFF
    await send_instr(dut, ADDI(4, 0, -1))
    addr, data = await exec_store(dut, STORE(4, 1, 1))
    assert data == 0xFF, f"STORE data=0xFF: beklenen 0xFF, gelen {hex(data)}"

    # PC STORE sonrasi ilerliyor mu
    # Iki NOP gonder: birinci NOP'tan sonra uo_out=PC kesin, orada pc_before al.
    # Sonra STORE + NOP, pc_after = pc_before + 2 olmali.
    await send_instr(dut, NOP())
    pc_before = int(dut.uo_out.value)
    await exec_store(dut, STORE(2, 1, 0))
    await send_instr(dut, NOP())
    pc_after = int(dut.uo_out.value)
    assert pc_after == (pc_before + 2) & 0xFF, f"STORE sonrasi PC ilerlemedi: beklenen {hex((pc_before+2)&0xFF)}, gelen {hex(pc_after)}"

    dut._log.info("STORE PASSED")


@cocotb.test()
async def test_project(dut):
    """tt_um_basic8 — 8-bit CPU full test suite"""
    clock = Clock(dut.clk, 100, unit="ns")
    cocotb.start_soon(clock.start())

    await check_i_type(dut)
    await check_r_type(dut)
    await check_addi_negative(dut)
    await check_beq(dut)
    await check_bne_loop(dut)
    await check_jal(dut)
    await check_r0_hardwired(dut)
    await check_load(dut)
    await check_store(dut)

    dut._log.info("=== All tests PASSED ===")
