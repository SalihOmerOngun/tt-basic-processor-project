module alu (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [2:0] sel,
    output reg  [7:0] result
);
    always @(*) begin
        case (sel)
            3'd0: result = a + b;
            3'd1: result = a - b;
            3'd2: result = a | b;
            3'd3: result = a ^ b;
            3'd4: result = a & b;
            3'd5: result = a << b[2:0];
            3'd6: result = a >> b[2:0];
            3'd7: result = $signed(a) >>> b[2:0];
            default: result = 8'd0;
        endcase
    end
endmodule
