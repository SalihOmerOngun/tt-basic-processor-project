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

    reg [7:0] regfile [0:7];
    reg [7:0] pc;
    reg [7:0] instr_hi;
    reg       mem_wait;
    reg [2:0] load_rd;

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

    wire [7:0] alu_b = (opcode == 4'b0000) ? regfile[instr[12:10]] : imm8;

    wire [2:0] alu_sel = (opcode == 4'b0000) ? funct3
                       : (opcode == 4'b0001) ? 3'b000
                       : (opcode == 4'b0010) ? 3'b100
                       : (opcode == 4'b0011) ? 3'b010
                       : (opcode == 4'b0100) ? 3'b011
                       :                       3'b000;

    wire [7:0] alu_out;
    alu alu_inst (
        .a      (rs1_val),
        .b      (alu_b),
        .sel    (alu_sel),
        .result (alu_out)
    );

    wire op_load  = (opcode == 4'b1000);
    wire op_store = (opcode == 4'b1001);

    wire [7:0] mem_addr = rs1_val + imm8;

    wire mem_valid = uio_in[3];
    wire mem_we    = op_store && uio_in[1];

    reg [7:0] wdata;
    always @(*) begin
        case (opcode)
            4'b0111: wdata = pc + 8'd1;
            default: wdata = alu_out;
        endcase
    end

    wire wr_en = (opcode == 4'b0000) || (opcode == 4'b0001) ||
                 (opcode == 4'b0010) || (opcode == 4'b0011) ||
                 (opcode == 4'b0100) || (opcode == 4'b0111);

    wire beq_taken = (opcode == 4'b0101) && (rs1_val == rs2_val);
    wire bne_taken = (opcode == 4'b0110) && (rs1_val != rs2_val);
    wire jal_taken = (opcode == 4'b0111);

    wire       pc_jump   = beq_taken | bne_taken | jal_taken;
    wire [7:0] pc_target = pc + imm8;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 8; i = i + 1)
                regfile[i] <= 8'd0;
            pc       <= 8'd0;
            instr_hi <= 8'd0;
            mem_wait <= 1'b0;
            load_rd  <= 3'd0;
        end else if (ena) begin

            if (uio_in[0])
                instr_hi <= ui_in;

            if (uio_in[1] && !mem_wait) begin
                if (op_load) begin
                    mem_wait <= 1'b1;
                    load_rd  <= rd;
                end else if (op_store) begin
                    pc <= pc + 8'd1;
                end else begin
                    if (wr_en && rd != 3'd0)
                        regfile[rd] <= wdata;
                    if (pc_jump)
                        pc <= pc_target;
                    else
                        pc <= pc + 8'd1;
                end
            end

            if (mem_wait && mem_valid) begin
                if (load_rd != 3'd0)
                    regfile[load_rd] <= ui_in;
                pc       <= pc + 8'd1;
                mem_wait <= 1'b0;
            end

        end
    end

    assign uo_out  = (op_load || op_store) ? mem_addr : pc;
    assign uio_out = rs2_val;
    assign uio_oe  = 8'b1111_0111;

    wire _unused = &{ena, uio_in[7:4], uio_in[2], mem_we, load_rd, 1'b0};

endmodule
