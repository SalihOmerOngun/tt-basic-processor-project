/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_basic8 (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);


    reg [7:0] regfile [7:0];
 
    reg [7:0] pc;
 
    reg [7:0] instr_hi;
 
    wire [15:0] instr   = {instr_hi, ui_in};
 
    wire [3:0]  opcode  = instr[3:0];
    wire [2:0]  rd      = instr[6:4];
    wire [2:0]  rs1_idx = instr[9:7];
    wire [2:0]  rs2_idx = instr[6:4];  
    wire [2:0]  funct3  = instr[15:13];
    wire [5:0]  imm6    = instr[15:10];
    wire [7:0]  imm8    = {{2{imm6[5]}}, imm6};  
 
    wire [7:0]  rs1_val = regfile[rs1_idx];
    wire [7:0]  rs2_val = regfile[rs2_idx];
 
    wire [7:0] alu_out;
    alu alu_inst (
        .a      (rs1_val),
        .b      (regfile[instr[12:10]]),   // R-type rs2 from [12:10]
        .sel    (funct3),
        .result (alu_out)
    );
 
    reg [7:0] wdata;
    always @(*) begin
        case (opcode)
            4'b0000: wdata = alu_out;               // R-type
            4'b0001: wdata = rs1_val + imm8;        // ADDI
            4'b0010: wdata = rs1_val & {2'b00,imm6};// ANDI (zero-ext)
            4'b0011: wdata = rs1_val | {2'b00,imm6};// ORI  (zero-ext)
            4'b0100: wdata = rs1_val ^ {2'b00,imm6};// XORI (zero-ext)
            4'b0111: wdata = pc + 8'd1;             // JAL: rd = PC+1
            default: wdata = 8'd0;
        endcase
    end
 
    wire wr_en = (opcode == 4'b0000) || (opcode == 4'b0001) ||
                 (opcode == 4'b0010) || (opcode == 4'b0011) ||
                 (opcode == 4'b0100) || (opcode == 4'b0111);
 
    wire beq_taken = (opcode == 4'b0101) && (rs1_val == rs2_val);
    wire bne_taken = (opcode == 4'b0110) && (rs1_val != rs2_val);
    wire jal_taken = (opcode == 4'b0111);
 
    wire        pc_jump   = beq_taken | bne_taken | jal_taken;
    wire [7:0]  pc_target = pc + imm8;
 
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 8; i = i + 1)
                regfile[i] <= 8'd0;
            pc       <= 8'd0;
            instr_hi <= 8'd0;
        end else if (ena) begin
 
            // Phase 1: latch high byte
            if (uio_in[0])
                instr_hi <= ui_in;
 
            // Phase 2: execute
            if (uio_in[1]) begin
                // register write
                if (wr_en && rd != 3'd0)
                    regfile[rd] <= wdata;
 
                // PC update
                if (pc_jump)
                    pc <= pc_target;
                else
                    pc <= pc + 8'd1;
            end
        end
    end
 
    assign uo_out  = pc;
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;
 
    wire _unused = &{ena, uio_in[7:2], 1'b0};

endmodule