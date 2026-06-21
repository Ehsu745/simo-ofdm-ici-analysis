%% =====================================================================
%  SIMO-OFDM 多接收天線 BER 模擬 (Monte Carlo) — v2 修正版
%  ---------------------------------------------------------------------
%  v2 相對 v1 的主要修正 (詳見 FIXES.md):
%    1. 雜訊功率改用「量測接收訊號功率 / SNR」, 不再用通道 tap 功率
%    2. 複數雜訊正確拆分 I/Q 各 sigma^2/2, 修正遺漏的因子 2
%    3. 每根天線獨立生成雜訊 (移除天線間相關性, 不再高估分集增益)
%    4. 等化器可切換 ZF / MMSE (v1 寫死為 ZF 左除, 與報告正文 MMSE 不符)
%    5. 移除物理上對不上系統的 Q-function 理論線
%    6. 指數擬合改為僅對 BER>0 的點做 log 線性擬合, 解決 BER 觸底退化
%    7. 橫軸/SNR 標註明確為 Eb/N0 (QPSK: Es/N0 = Eb/N0 + 3dB)
% =====================================================================

clc; clear all; close all;
rng(42);   % 固定種子, 確保可重現

%% ---- 系統參數 ----
qpsk   = 1/sqrt(2)*[1+1j, -1+1j, -1-1j, 1-1j];  % QPSK, 每符號功率 = 1
number = 200;        % OFDM block 數
P = 15; N = 8; L = 5; M = P - N;                 % CP 長度 M, 子載波 N, 通道階數 L

EbN0_dB     = 10;                 % 每位元 SNR (Eb/N0), 標準慣例
bits_per_sym = 2;                 % QPSK = 2 bits/symbol
EsN0_dB     = EbN0_dB + 10*log10(bits_per_sym);  % Es/N0 = Eb/N0 + 3dB
EsN0_lin    = 10^(EsN0_dB/10);

output_size = [2 3 4 5 6];        % 接收天線數掃描
num_trials  = 1000;               % Monte Carlo 次數

% ---- 等化器選擇: 'ZF' 或 'MMSE' ----
eq_type = 'MMSE';

BER_avg = zeros(size(output_size));

%% ---- Monte Carlo 主迴圈 ----
for trial = 1:num_trials
    % 每次 trial 重新抽 通道 / 資料 (雜訊在天線迴圈內各自生成)
    x = randsrc(N, number, qpsk);
    h_size = L + 1;
    h = randn(h_size, max(output_size)) + 1j*randn(h_size, max(output_size));

    BER = zeros(size(output_size));
    for index = 1:length(output_size)
        n_ant = output_size(index);

        % 頻域通道響應 (N 點 DFT)
        d = fftCal(h(:, 1:n_ant), N);

        % ---- 發射端 ----
        s = ifft(x);
        u = [s(N-M+1:N, :); s];          % 加 CP
        input_signal = reshape(u, P*number, 1);

        % ---- 傳送 + 接收 (每天線獨立雜訊) ----
        y_all = zeros(N, number-1, n_ant);
        for i = 1:n_ant
            rx = conv(h(:, i), input_signal);

            % [修正核心] 量測「這一級」實際訊號功率, 據此定雜訊
            Ps     = mean(abs(rx).^2);
            sigma2 = Ps / EsN0_lin;              % 複數雜訊總變異數
            % 複數雜訊: I/Q 各 sigma2/2, 每天線獨立
            noise  = sqrt(sigma2/2) * ...
                     (randn(size(rx)) + 1j*randn(size(rx)));
            rx = rx + noise;

            % ---- 接收端: 去暫態 / 去 CP / FFT ----
            % 註: 丟掉第 1 個 block 以避開 conv 邊界暫態 (off-by-one 為刻意設計)
            output_signal = rx(P+1 : P*number);
            v = reshape(output_signal, P, number-1);
            z = v(M+1:P, :);
            y_all(:, :, i) = fft(z);
        end

        % ---- 等化 (per-subcarrier) ----
        x_hat = zeros(N, number-1);
        for nn = 1:number-1
            for k = 1:N
                H = d(k, 1:n_ant).';            % 通道向量 (天線數 x 1)
                y = squeeze(y_all(k, nn, :));   % 接收向量 (天線數 x 1)

                switch eq_type
                    case 'ZF'
                        % 最小二乘 / ZF: 純逆通道, 不考慮雜訊
                        x_hat(k, nn) = H \ y;
                    case 'MMSE'
                        % MMSE: W = (H^H H + sigma2 I)^-1 H^H
                        % 此處 H 為 (天線數 x 1), H^H H 為純量
                        sigma2_eq = Ps / EsN0_lin;
                        W = (H'*H + sigma2_eq) \ H';   % (1 x 天線數)
                        x_hat(k, nn) = W * y;
                    otherwise
                        error('eq_type 必須是 ZF 或 MMSE');
                end
            end
        end

        % ---- QPSK 硬判別 ----
        x_hat = qpskSlice(x_hat);

        % ---- 符號錯誤率 (此處以符號比對, 等同 SER) ----
        correct = sum(sum(x_hat == x(:, 2:number)));
        BER(index) = (N*(number-1) - correct) / (N*(number-1));
    end
    BER_avg = BER_avg + BER;
end
BER_avg = BER_avg / num_trials;

%% ---- 結果輸出 ----
fprintf('\n=== 等化器: %s | Eb/N0 = %d dB (Es/N0 = %.1f dB) ===\n', ...
        eq_type, EbN0_dB, EsN0_dB);
for index = 1:length(output_size)
    fprintf('  天線數 %d : BER = %.4e\n', output_size(index), BER_avg(index));
end

%% ---- 指數擬合 (僅對 BER>0 的點, 避免觸底退化) ----
valid = BER_avg > 0;
figure; hold on; grid on;
plot(output_size, max(BER_avg, eps), 'o-', 'LineWidth', 2, ...
     'DisplayName', sprintf('Simulated BER (%s)', eq_type));

if nnz(valid) >= 2
    % 對 log(BER) 做線性擬合 => BER = a*exp(b*n)
    p = polyfit(output_size(valid), log(BER_avg(valid)), 1);
    b = p(1); a = exp(p(2));
    n_fine = linspace(min(output_size), max(output_size), 100);
    plot(n_fine, a*exp(b*n_fine), '--', 'LineWidth', 2, ...
         'DisplayName', 'Exponential fit');
    fprintf('\n擬合: BER = %.4e * exp(%.4e * N_antennas)\n', a, b);
else
    fprintf('\n[提示] 有效點不足 (BER 多數觸底), 略過擬合。建議調低 Eb/N0。\n');
end

set(gca, 'YScale', 'log');     % BER 用對數軸才看得出量級差異
xlabel('Number of Receive Antennas');
ylabel('BER (log scale)');
title(sprintf('SIMO-OFDM BER vs. Rx Antennas (%s, Eb/N0=%ddB)', eq_type, EbN0_dB));
legend('Location', 'Best');
hold off;

%% ===================== 子函式 =====================
function x_hat = qpskSlice(x_hat)
% QPSK 最近鄰硬判別 (依象限)
    r = real(x_hat); i = imag(x_hat);
    x_hat(r>0  & i>0)  = 1/sqrt(2)*( 1+1j);
    x_hat(r<0  & i>0)  = 1/sqrt(2)*(-1+1j);
    x_hat(r<0  & i<0)  = 1/sqrt(2)*(-1-1j);
    x_hat(r>=0 & i<0)  = 1/sqrt(2)*( 1-1j);
end

function ret = fftCal(h, N)
% 將通道脈衝響應補零至 N 點後做 DFT, 得頻域響應
    ret = zeros(N, size(h,2));
    for i = 1:size(h, 2)
        ret(:, i) = fft([h(:, i); zeros(N - size(h(:,i),1), 1)]);
    end
end
