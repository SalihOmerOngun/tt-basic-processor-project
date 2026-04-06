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

def NOP():
    return ADDI(0, 0, 0)

# funct3 constants
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

async def read_reg(dut, idx):
    """Read register directly via cocotb internal signal access."""
    dut.uio_in.value = (idx & 0x7) << 2
    await Timer(2, unit="ns")
    val = int(dut.uio_out.value)
    dut.uio_in.value = 0
    return val

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
    dut._log.info("--- BNE backward loop (count 0→3) ---")
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



@cocotb.test()
async def test_project(dut):
    """tt_um_basic8 — 8-bit CPU full test suite"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await check_i_type(dut)
    await check_r_type(dut)
    await check_addi_negative(dut)
    await check_beq(dut)
    await check_bne_loop(dut)
    await check_jal(dut)
    await check_r0_hardwired(dut)

    dut._log.info("=== All tests PASSED ===")