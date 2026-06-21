%% =====================================================================
%  SIMO-OFDM 星座圖 + 單次 BER 觀察 — v2 修正版
%  (與 multiple_antenna_compare_MONTE_v2.m 共用相同的雜訊/等化修正)
%  本檔用途: 視覺化「隨天線數增加, QPSK 星座收斂」的現象
% =====================================================================

clc; clear all; close all;
rng(42);

%% ---- 系統參數 ----
qpsk   = 1/sqrt(2)*[1+1j, -1+1j, -1-1j, 1-1j];
number = 200;
P = 15; N = 8; L = 5; M = P - N;

EbN0_dB      = 13;
bits_per_sym = 2;
EsN0_dB      = EbN0_dB + 10*log10(bits_per_sym);
EsN0_lin     = 10^(EsN0_dB/10);

output_size = [2 3 4 5 6];
BER = zeros(size(output_size));

eq_type = 'MMSE';   % 'ZF' 或 'MMSE'

% 固定 通道 / 資料 (單次觀察)
x = randsrc(N, number, qpsk);
h_size = L + 1;
h = randn(h_size, max(output_size)) + 1j*randn(h_size, max(output_size));

for index = 1:length(output_size)
    n_ant = output_size(index);
    d = fftCal(h(:, 1:n_ant), N);

    % 發射端
    s = ifft(x);
    u = [s(N-M+1:N, :); s];
    input_signal = reshape(u, P*number, 1);

    % 傳送 + 接收 (每天線獨立雜訊)
    y_all = zeros(N, number-1, n_ant);
    for i = 1:n_ant
        rx = conv(h(:, i), input_signal);
        Ps     = mean(abs(rx).^2);
        sigma2 = Ps / EsN0_lin;
        noise  = sqrt(sigma2/2) * (randn(size(rx)) + 1j*randn(size(rx)));
        rx = rx + noise;

        output_signal = rx(P+1 : P*number);
        v = reshape(output_signal, P, number-1);
        z = v(M+1:P, :);
        y_all(:, :, i) = fft(z);
    end

    % 等化
    x_hat = zeros(N, number-1);
    for nn = 1:number-1
        for k = 1:N
            H = d(k, 1:n_ant).';
            y = squeeze(y_all(k, nn, :));
            switch eq_type
                case 'ZF'
                    x_hat(k, nn) = H \ y;
                case 'MMSE'
                    sigma2_eq = Ps / EsN0_lin;
                    W = (H'*H + sigma2_eq) \ H';
                    x_hat(k, nn) = W * y;
            end
        end
    end
    x_plot = x_hat;                 % 判別前 (畫星座用)
    x_hat  = qpskSlice(x_hat);      % 判別後

    correct = sum(sum(x_hat == x(:, 2:number)));
    BER(index) = (N*(number-1) - correct) / (N*(number-1));
    fprintf('天線數 %d : BER = %.4e\n', n_ant, BER(index));

    % ---- 星座圖 ----
    figure; hold on; grid on;
    scatter(real(x(:)),      imag(x(:)),      40, 'bo', ...
            'DisplayName', '發射信號', 'LineWidth', 1.2);
    scatter(real(x_plot(:)), imag(x_plot(:)), 18, 'rx', ...
            'DisplayName', '判別前接收信號');
    xlabel('In-Phase (I)'); ylabel('Quadrature (Q)');
    title(sprintf('QPSK 星座圖 — %d 接收天線 (%s)', n_ant, eq_type));
    legend('Location','Best'); axis([-1.5 1.5 -1.5 1.5]); axis square;
    hold off;
end

%% ---- BER vs 天線數 ----
figure;
semilogy(output_size, max(BER, eps), 'o-', 'LineWidth', 2);
grid on;
xlabel('Number of Receive Antennas');
ylabel('BER (log scale)');
title(sprintf('BER vs. Rx Antennas (%s, Eb/N0=%ddB)', eq_type, EbN0_dB));
legend(sprintf('Simulated BER (%s)', eq_type), 'Location', 'Best');

%% ===================== 子函式 =====================
function x_hat = qpskSlice(x_hat)
    r = real(x_hat); i = imag(x_hat);
    x_hat(r>0  & i>0)  = 1/sqrt(2)*( 1+1j);
    x_hat(r<0  & i>0)  = 1/sqrt(2)*(-1+1j);
    x_hat(r<0  & i<0)  = 1/sqrt(2)*(-1-1j);
    x_hat(r>=0 & i<0)  = 1/sqrt(2)*( 1-1j);
end

function ret = fftCal(h, N)
    ret = zeros(N, size(h,2));
    for i = 1:size(h, 2)
        ret(:, i) = fft([h(:, i); zeros(N - size(h(:,i),1), 1)]);
    end
end
