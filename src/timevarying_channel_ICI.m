%% =====================================================================
%  時變通道 (都卜勒) 模組 — A 階段
%  ---------------------------------------------------------------------
%  目的: 在 SIMO-OFDM v2 基礎上, 引入「一個 OFDM 符號內通道隨時間變化」,
%        破壞子載波正交性, 複現 ICI (Inter-Carrier Interference) 現象。
%
%  提供兩種時變模型 (chan_mode 切換):
%    'phase' : 簡化線性相位旋轉  -> 教學用, 直觀展示 ICI 來源
%    'jakes' : Jakes sum-of-sinusoids -> 業界標準, 嚴謹驗證
%
%  關鍵參數: 歸一化都卜勒頻率 fdTs_norm = 最大都卜勒頻率 / 子載波間距
%            (= fd * Ts, Ts 為 OFDM 符號週期)
%            值越大 -> 通道在符號內變化越快 -> ICI 越嚴重
%            參考: 行動 WiMAX 環境 fdTs ~0.2 時 ICI 已需進階等化
% =====================================================================

clc; clear all; close all;
rng(42);

%% ---- 系統參數 (與 v2 對齊) ----
qpsk   = 1/sqrt(2)*[1+1j, -1+1j, -1-1j, 1-1j];
N = 64;                       % 子載波數 (加大以看清 ICI 洩漏)
M = 16;                       % CP 長度
P = N + M;
L = 5;                        % 通道階數 (多徑 tap 數 = L+1)

EbN0_dB  = 20;                % 先用高 SNR, 凸顯 ICI (而非雜訊) 的影響
EsN0_lin = 10^((EbN0_dB + 10*log10(2))/10);

% 歸一化都卜勒頻率掃描 (0 = 靜態, 越大 ICI 越強)
fdTs_list = [0, 0.05, 0.1, 0.2];

chan_mode = 'jakes';          % 'phase' 或 'jakes'

%% =====================================================================
%  Demo 1: 星座圖 — 靜態 vs 高都卜勒
% =====================================================================
number = 200;
x = randsrc(N, number, qpsk);

figure('Name','ICI 星座圖對比');
for fi = 1:length(fdTs_list)
    fdTs = fdTs_list(fi);

    % 通道脈衝響應 (準靜態基底)
    h0 = (randn(L+1,1) + 1j*randn(L+1,1)) / sqrt(2*(L+1));

    x_hat = ofdm_tx_rx_timevarying(x, h0, N, M, P, L, fdTs, ...
                                   chan_mode, EsN0_lin);

    subplot(2,2,fi);
    scatter(real(x_hat(:)), imag(x_hat(:)), 8, 'r.'); hold on;
    scatter(real(qpsk), imag(qpsk), 60, 'bo', 'LineWidth', 1.5);
    grid on; axis([-1.5 1.5 -1.5 1.5]); axis square;
    title(sprintf('f_dT_s = %.2f', fdTs));
    xlabel('I'); ylabel('Q');
end
sgtitle(sprintf('ICI 隨歸一化都卜勒頻率增大而星座散開 (%s 模型)', chan_mode));

%% =====================================================================
%  Demo 2: 子載波洩漏 — 只激發單一子載波, 看功率漏到鄰居
% =====================================================================
figure('Name','子載波洩漏');
probe = zeros(N, 1);
probe(N/2) = 1;               % 只在中間子載波放能量

for fi = 1:length(fdTs_list)
    fdTs = fdTs_list(fi);
    h0 = (randn(L+1,1) + 1j*randn(L+1,1)) / sqrt(2*(L+1));

    % 對多次通道實現取平均 (單次雜亂, 平均才看得出洩漏的統計形狀)
    Navg = 200;
    Pwr = zeros(N, 1);
    for r = 1:Navg
        h0r = (randn(L+1,1) + 1j*randn(L+1,1)) / sqrt(2*(L+1));
        Y = ofdm_leakage_probe(probe, h0r, N, M, P, L, fdTs, chan_mode);
        Pwr = Pwr + abs(Y).^2;
    end
    Pwr = Pwr / max(Pwr);              % 以主瓣為 0 dB 參考

    subplot(2,2,fi);
    % 用 dB 軸: 旁瓣常只有主瓣 1% (-20dB), 線性軸看不見, 必須對數軸
    stem(0:N-1, 10*log10(Pwr + eps), 'filled', 'MarkerSize', 3);
    grid on; xlim([N/2-10, N/2+10]); ylim([-40, 2]);
    title(sprintf('f_dT_s = %.2f', fdTs));
    xlabel('子載波索引'); ylabel('相對功率 (dB)');
end
sgtitle('單一子載波激發 (dB 軸): 都卜勒越大, 旁瓣洩漏越高 (= ICI)');

%% =====================================================================
%  Demo 3: ICI 功率 / BER vs 歸一化都卜勒頻率
% =====================================================================
fdTs_fine = linspace(0, 0.25, 11);
num_trials = 50;
BER_curve = zeros(size(fdTs_fine));
ICI_dB    = zeros(size(fdTs_fine));

for fi = 1:length(fdTs_fine)
    fdTs = fdTs_fine(fi);
    ber_acc = 0; ici_acc = 0;
    for t = 1:num_trials
        xt = randsrc(N, number, qpsk);
        h0 = (randn(L+1,1) + 1j*randn(L+1,1)) / sqrt(2*(L+1));

        [x_hat, ici_power, sig_power] = ...
            ofdm_tx_rx_timevarying(xt, h0, N, M, P, L, fdTs, ...
                                   chan_mode, EsN0_lin);
        x_sliced = qpskSlice(x_hat);
        ber_acc = ber_acc + mean(x_sliced(:) ~= xt(:));
        ici_acc = ici_acc + ici_power / sig_power;
    end
    BER_curve(fi) = ber_acc / num_trials;
    ICI_dB(fi)    = 10*log10(ici_acc / num_trials + eps);
end

figure('Name','ICI/BER vs 都卜勒');
subplot(1,2,1);
semilogy(fdTs_fine, max(BER_curve, eps), 'o-', 'LineWidth', 2);
grid on; xlabel('歸一化都卜勒頻率 f_dT_s'); ylabel('BER');
title('BER 隨都卜勒上升 (傳統等化失效)');

subplot(1,2,2);
plot(fdTs_fine, ICI_dB, 's-', 'LineWidth', 2);
grid on; xlabel('歸一化都卜勒頻率 f_dT_s'); ylabel('ICI / Signal (dB)');
title('ICI 功率相對訊號功率');

fprintf('完成。chan_mode = %s\n', chan_mode);

%% =====================================================================
%  核心函式: 時變通道下的 OFDM 收發
% =====================================================================
function [x_hat, ici_power, sig_power] = ...
         ofdm_tx_rx_timevarying(x, h0, N, M, P, L, fdTs, chan_mode, EsN0_lin)
    number = size(x, 2);

    % 發射端
    s = ifft(x);
    u = [s(N-M+1:N, :); s];
    tx = reshape(u, P*number, 1);

    % ---- 時變通道: 每個時間樣本的 tap 都隨時間變化 ----
    Ntot = length(tx);
    h_t = timevarying_taps(h0, Ntot, fdTs, N, chan_mode);  % (L+1 x Ntot)

    % 逐樣本卷積 (時變 -> 不能用單一 conv)
    rx = zeros(Ntot, 1);
    for n = 1:Ntot
        for l = 0:L
            if n-l >= 1
                rx(n) = rx(n) + h_t(l+1, n) * tx(n-l);
            end
        end
    end

    % 加雜訊
    Ps     = mean(abs(rx).^2);
    sigma2 = Ps / EsN0_lin;
    rx = rx + sqrt(sigma2/2)*(randn(Ntot,1)+1j*randn(Ntot,1));

    % 接收端: 去 CP + FFT
    rxm = reshape(rx, P, number);
    rxm = rxm(M+1:P, :);            % 去 CP
    Y   = fft(rxm);                 % 頻域接收

    % 單抽頭等化: 每個符號用「該符號中點」的通道估計
    % (實務上可由導頻估得; 故意不補償符號內變化 -> 凸顯 ICI 殘留)
    x_hat = zeros(N, number);
    for sym = 1:number
        mid   = (sym-1)*P + M + round(N/2);     % 該符號中點時間索引
        mid   = min(mid, size(h_t,2));
        h_mid = h_t(:, mid);
        d_mid = fft([h_mid; zeros(N-(L+1),1)]);
        x_hat(:, sym) = Y(:, sym) ./ d_mid;
    end

    % ---- ICI 功率量測 (以符號中點通道為參考的對角 vs 非對角能量) ----
    % 簡化估計: 比較等化後與理想 QPSK 的偏差能量
    ideal = x;
    ici_power = mean(abs(x_hat(:) - ideal(:)).^2);
    sig_power = mean(abs(ideal(:)).^2);
end

%% ---- 子載波洩漏探針 (無雜訊, 純看 ICI) ----
function Y = ofdm_leakage_probe(probe, h0, N, M, P, L, fdTs, chan_mode)
    s = ifft(probe);
    u = [s(N-M+1:N); s];
    tx = u;
    Ntot = length(tx);
    h_t = timevarying_taps(h0, Ntot, fdTs, N, chan_mode);

    rx = zeros(Ntot, 1);
    for n = 1:Ntot
        for l = 0:L
            if n-l >= 1
                rx(n) = rx(n) + h_t(l+1, n) * tx(n-l);
            end
        end
    end
    rx = rx(M+1:P);
    Y = fft(rx);
end

%% ---- 時變 tap 生成: 兩種模型 ----
function h_t = timevarying_taps(h0, Ntot, fdTs, N, chan_mode)
    % 回傳 (L+1 x Ntot) 每樣本的 tap。
    % 關鍵修正: 每個 tap (及每條正弦路徑) 各自獨立衰落, 各 tap 都卜勒
    %           方向不同 -> 不會疊加成同向的固定頻偏(CFO), 純粹反映
    %           「符號內通道變化」這個真正產生 ICI 的成分。
    % 註: h0 僅用來決定 tap 數; 振幅在此重新獨立抽樣以確保各 tap 去相關。
    Ltap = length(h0);
    h_t  = zeros(Ltap, Ntot);

    % 歸一化都卜勒 fdTs (相對子載波間距/整個 N 樣本符號) -> 每樣本頻率
    fd_sample = fdTs / N;
    t = (0:Ntot-1);

    switch chan_mode
        case 'phase'
            % 簡化模型: 每 tap 單一隨機都卜勒分量 (各 tap 方向獨立)
            % 直觀展示「通道在符號內不再是常數 -> FFT 不再對角 -> ICI」
            for l = 1:Ltap
                fd_m = fd_sample * cos(2*pi*rand);          % 各 tap 不同方向
                phi  = 2*pi*rand;
                amp  = (randn + 1j*randn) / sqrt(2*Ltap);   % 獨立複高斯振幅
                h_t(l, :) = amp * exp(1j*(2*pi*fd_m*t + phi));
            end

        case 'jakes'
            % Jakes sum-of-sinusoids: 每 tap 為多條正弦疊加, 各 tap 獨立
            % 自相關 ~ J0(2*pi*fd*dt), 業界標準 Rayleigh 時變模型
            Nsin = 16;
            for l = 1:Ltap
                ht = zeros(1, Ntot);
                for m = 1:Nsin
                    theta = 2*pi*m/Nsin;              % 入射角均勻分布
                    fd_m  = fd_sample * cos(theta);
                    phi   = 2*pi*rand;
                    ht = ht + exp(1j*(2*pi*fd_m*t + phi));
                end
                ht  = ht / sqrt(Nsin);
                amp = (randn + 1j*randn) / sqrt(2*Ltap); % 獨立複高斯振幅
                h_t(l, :) = amp * ht;
            end
    end
end

%% ---- QPSK 判別 ----
function x_hat = qpskSlice(x_hat)
    r = real(x_hat); i = imag(x_hat);
    x_hat(r>0  & i>0)  = 1/sqrt(2)*( 1+1j);
    x_hat(r<0  & i>0)  = 1/sqrt(2)*(-1+1j);
    x_hat(r<0  & i<0)  = 1/sqrt(2)*(-1-1j);
    x_hat(r>=0 & i<0)  = 1/sqrt(2)*( 1-1j);
end
